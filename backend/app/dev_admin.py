"""LOCAL OPERATOR CLI. List test users and assisted-onboarding requests. No HTTP admin API."""
from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import engine, init_db
from .local_auth import LocalUser
from .saas import Workspace
from .connections import AssistedSetupRequest, SquareConnection


def main():
    init_db()
    with Session(engine) as db:
        print('=== Local TableSignal development accounts ===')
        for user in db.scalars(select(LocalUser).order_by(LocalUser.created_at)).all():
            w=db.scalar(select(Workspace).where(Workspace.owner_sub==user.id))
            connected=bool(w and db.scalar(select(SquareConnection).where(SquareConnection.workspace_id==w.id)))
            print(f'Email={user.email} | restaurant={w.name if w else "not set"} | '
                  f'plan={w.subscription_plan if w else "none"} | Square Sandbox={connected}')
        print('\n=== Assisted setup requests (stored locally; not delivered) ===')
        for request in db.scalars(select(AssistedSetupRequest).order_by(AssistedSetupRequest.created_at.desc())).all():
            w=db.get(Workspace,request.workspace_id)
            print(f'{request.created_at[:19]} | restaurant={w.name if w else "unknown"} | '
                  f'provider={request.provider} | status={request.status} | '
                  f'context={request.note[:80]}')


if __name__=='__main__':main()
