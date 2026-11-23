"""Workspace membership, roles, invites and account deletion (docs/PRODUCT_PLAN.md M2).

Every signed-in subject belongs to exactly one workspace, as `owner` or `manager`.
Owners control the data connection, billing, team and deletion; managers can use the
product (dashboard, sync, decisions, analyst). The first sign-in creates a workspace
with the caller as owner, so nothing about signup changes for a solo owner.
"""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, Integer, String, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from . import config
from .database import Base, engine
from .local_auth import authenticated_subject

ROLES = ('owner', 'manager')
INVITE_TTL_SECONDS = 7 * 24 * 3600
ACTIVE_BILLING = ('active', 'trialing', 'past_due')


class WorkspaceMember(Base):
    __tablename__ = 'workspace_members'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True)
    subject: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(254), default='')
    created_at: Mapped[str] = mapped_column(String(40))


class WorkspaceInvite(Base):
    __tablename__ = 'workspace_invites'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('saas_workspaces.id'), index=True)
    role: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(254))
    created_by: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[str] = mapped_column(String(40))
    expires_at: Mapped[int] = mapped_column(Integer)
    accepted_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def resolve(db: Session, subject: str):
    """(workspace, role) for a subject, creating an owner workspace on first sign-in.

    A new user's first page load sends several requests at once; if two race to create the
    workspace, the loser's insert hits the unique constraint and it re-reads the winner's row.
    """
    for _ in range(3):
        found = _lookup(db, subject)
        if found:
            return found
        try:
            return _create_owner_workspace(db, subject)
        except IntegrityError:
            db.rollback()
    raise HTTPException(503, 'Your workspace is being set up. Refresh in a moment.')


def _lookup(db: Session, subject: str):
    from .saas import Workspace
    member = db.scalar(select(WorkspaceMember).where(WorkspaceMember.subject == subject))
    if member:
        workspace = db.get(Workspace, member.workspace_id)
        if workspace:
            return workspace, member.role
        db.delete(member)
        db.commit()
    return None


def _create_owner_workspace(db: Session, subject: str):
    from .saas import Workspace
    workspace = db.scalar(select(Workspace).where(Workspace.owner_sub == subject))
    if workspace is None:
        workspace = Workspace(id=str(uuid.uuid4()), owner_sub=subject, created_at=_now())
        db.add(workspace)
        db.flush()
    # Workspaces created before memberships existed get their owner row on first use.
    db.add(WorkspaceMember(id=str(uuid.uuid4()), workspace_id=workspace.id, subject=subject,
                           role='owner', created_at=_now()))
    db.commit()
    db.refresh(workspace)
    return workspace, 'owner'


def owner_subject(sub: str = Depends(authenticated_subject)) -> str:
    """Dependency for actions only the workspace owner may take."""
    with Session(engine) as db:
        _, role = resolve(db, sub)
    if role != 'owner':
        raise HTTPException(403, 'Only the workspace owner can do this. Ask the owner of this workspace.')
    return sub


def _workspace_has_data(db: Session, workspace_id: str) -> bool:
    for table in _workspace_tables():
        if table.name in ('workspace_members', 'tablesignal_onboarding_progress'):
            continue
        if db.scalar(select(func.count()).select_from(table).where(table.c.workspace_id == workspace_id)):
            return True
    return False


def _workspace_tables():
    return [t for t in Base.metadata.sorted_tables if 'workspace_id' in t.c]


def _delete_workspace(db: Session, workspace_id: str) -> None:
    from .saas import Workspace
    # Children first (reverse dependency order), then the workspace row itself.
    for table in reversed(_workspace_tables()):
        db.execute(delete(table).where(table.c.workspace_id == workspace_id))
    db.execute(delete(Workspace.__table__).where(Workspace.id == workspace_id))


router = APIRouter(prefix='/api/team', tags=['Team and account'])


class InviteCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    role: str = Field(default='manager', pattern='^manager$')


class InviteAccept(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class DeleteRequest(BaseModel):
    confirm: str = Field(min_length=1, max_length=120)


@router.get('')
def team(sub: str = Depends(authenticated_subject)):
    with Session(engine) as db:
        workspace, role = resolve(db, sub)
        members = db.scalars(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id)
                             .order_by(WorkspaceMember.created_at)).all()
        invites = db.scalars(select(WorkspaceInvite).where(
            WorkspaceInvite.workspace_id == workspace.id, WorkspaceInvite.accepted_at.is_(None),
            WorkspaceInvite.expires_at > int(time.time()))).all() if role == 'owner' else []
        return {
            'workspace_name': workspace.name, 'my_role': role,
            'members': [{'id': m.id, 'role': m.role, 'email': m.email, 'is_me': m.subject == sub,
                         'joined_at': m.created_at} for m in members],
            'pending_invites': [{'id': i.id, 'email': i.email, 'role': i.role, 'created_at': i.created_at,
                                 'expires_at': i.expires_at} for i in invites],
        }


@router.post('/invites', status_code=201)
def create_invite(payload: InviteCreate, sub: str = Depends(owner_subject)):
    token = secrets.token_urlsafe(32)
    with Session(engine) as db:
        workspace, _ = resolve(db, sub)
        open_invites = db.scalar(select(func.count()).select_from(WorkspaceInvite).where(
            WorkspaceInvite.workspace_id == workspace.id, WorkspaceInvite.accepted_at.is_(None)))
        if open_invites >= 20:
            raise HTTPException(429, 'Too many pending invites. Revoke some first.')
        invite = WorkspaceInvite(id=str(uuid.uuid4()), token_hash=_hash(token), workspace_id=workspace.id,
                                 role=payload.role, email=payload.email.strip().lower(), created_by=sub,
                                 created_at=_now(), expires_at=int(time.time()) + INVITE_TTL_SECONDS)
        db.add(invite)
        db.commit()
        # The link is shown once to the owner; only its hash is stored.
        return {'id': invite.id, 'email': invite.email, 'role': invite.role, 'expires_at': invite.expires_at,
                'invite_url': f'{config.app_url()}/join?token={token}'}


@router.post('/invites/{invite_id}/revoke')
def revoke_invite(invite_id: str, sub: str = Depends(owner_subject)):
    with Session(engine) as db:
        workspace, _ = resolve(db, sub)
        invite = db.get(WorkspaceInvite, invite_id)
        if not invite or invite.workspace_id != workspace.id or invite.accepted_at:
            raise HTTPException(404, 'Invite not found.')
        db.delete(invite)
        db.commit()
    return {'revoked': True}


@router.post('/invites/accept')
def accept_invite(payload: InviteAccept, sub: str = Depends(authenticated_subject)):
    with Session(engine) as db:
        invite = db.scalar(select(WorkspaceInvite).where(WorkspaceInvite.token_hash == _hash(payload.token)))
        if not invite or invite.accepted_at or invite.expires_at < int(time.time()):
            raise HTTPException(404, 'This invite link is invalid or has expired. Ask the owner for a new one.')
        current = db.scalar(select(WorkspaceMember).where(WorkspaceMember.subject == sub))
        if current and current.workspace_id == invite.workspace_id:
            raise HTTPException(409, 'You are already a member of this workspace.')
        if current:
            # Joining replaces an empty starter workspace; anything with data must be deleted deliberately.
            if current.role != 'owner' or _workspace_has_data(db, current.workspace_id):
                raise HTTPException(409, 'Your account already has its own workspace with data. '
                                         'Delete it under Settings before joining another.')
            _delete_workspace(db, current.workspace_id)
        db.add(WorkspaceMember(id=str(uuid.uuid4()), workspace_id=invite.workspace_id, subject=sub,
                               role=invite.role, email=invite.email, created_at=_now()))
        invite.accepted_at = _now()
        role = invite.role
        db.commit()
    return {'joined': True, 'role': role}


@router.post('/members/{member_id}/remove')
def remove_member(member_id: str, sub: str = Depends(owner_subject)):
    with Session(engine) as db:
        workspace, _ = resolve(db, sub)
        member = db.get(WorkspaceMember, member_id)
        if not member or member.workspace_id != workspace.id:
            raise HTTPException(404, 'Member not found.')
        if member.subject == sub:
            raise HTTPException(409, 'Owners cannot remove themselves. Delete the workspace instead.')
        db.delete(member)
        db.commit()
    return {'removed': True}


@router.post('/account/delete')
def delete_account(payload: DeleteRequest, sub: str = Depends(authenticated_subject)):
    """Owner: delete the workspace and all its data. Manager: leave the workspace."""
    with Session(engine) as db:
        workspace, role = resolve(db, sub)
        if role != 'owner':
            db.execute(delete(WorkspaceMember).where(WorkspaceMember.subject == sub))
            db.commit()
            return {'deleted': 'membership', 'notice': 'You have left the workspace.'}
        if payload.confirm.strip() != workspace.name:
            raise HTTPException(422, 'Type the workspace name exactly to confirm deletion.')
        if workspace.subscription_status in ACTIVE_BILLING:
            raise HTTPException(409, 'Cancel your subscription in the billing portal before deleting the workspace.')
        _delete_workspace(db, workspace.id)
        if config.auth_mode() == 'local':
            from .local_auth import LocalSession, LocalUser
            db.execute(delete(LocalSession).where(LocalSession.user_id == sub))
            db.execute(delete(LocalUser.__table__).where(LocalUser.id == sub))
        db.commit()
    return {'deleted': 'workspace',
            'notice': 'Your workspace and all imported data were deleted. Revoke TableSignal in Square '
                      '(Account & Settings → Apps) if you connected it.'}
