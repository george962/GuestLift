"""Local-only development accounts with Argon2id and revocable database sessions.

NOT a production authentication service. The Docker API must remain bound to
127.0.0.1; no hosted or sensitive merchant data is authorized by this module.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Annotated

from argon2 import PasswordHasher, exceptions as argon_errors
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, Integer, String, select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .database import Base, engine

router = APIRouter(prefix='/api/local-auth', tags=['Local development authentication'])
SESSION_COOKIE = 'tablesignal_dev_session'
SESSION_TTL = 7 * 24 * 60 * 60
PASSWORD_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16)
_ALLOWED_ORIGINS = {'http://localhost:3000', 'http://127.0.0.1:3000'}
_EMAIL_RE = re.compile(r'^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,}$')
_lock = threading.Lock()
_attempts: dict[str, deque[float]] = defaultdict(deque)


class LocalUser(Base):
    __tablename__ = 'local_users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)


class LocalSession(Base):
    __tablename__ = 'local_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('local_users.id'), index=True)
    csrf_token: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[int] = mapped_column(Integer, index=True, nullable=False)


class AuthCredentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ChangePassword(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized_email(value: str) -> str:
    address = value.strip().casefold()
    if not _EMAIL_RE.fullmatch(address):
        raise HTTPException(status_code=422, detail='Enter a valid email address.')
    return address


def _require_local_origin(request: Request) -> None:
    origin = request.headers.get('origin', '')
    if origin not in _ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail='Request must originate from the local TableSignal site.')


def _throttle(request: Request, identifier: str) -> None:
    # Best-effort defense in development only. Deploy behind a robust server-side limiter in production.
    ip = request.client.host if request.client else 'unknown'
    key = f'{ip}:{identifier}'
    now = time.monotonic()
    with _lock:
        items = _attempts[key]
        while items and now - items[0] > 300:
            items.popleft()
        if len(items) >= 12:
            raise HTTPException(status_code=429, detail='Too many attempts. Try again later.')
        items.append(now)
        if len(_attempts) > 10000:
            _attempts.clear()


def _cookie_settings() -> dict:
    return dict(key=SESSION_COOKIE, httponly=True, secure=os.getenv('GUESTLIFT_COOKIE_SECURE') == '1',
                samesite='strict', path='/', max_age=SESSION_TTL)


def _create_session(db: Session, user: LocalUser, response: Response) -> None:
    secret = secrets.token_urlsafe(48)
    db.add(LocalSession(token_hash=hashlib.sha256(secret.encode()).hexdigest(), user_id=user.id,
                        csrf_token=secrets.token_urlsafe(32), created_at=int(time.time()),
                        expires_at=int(time.time()) + SESSION_TTL))
    db.commit()
    response.set_cookie(value=secret, **_cookie_settings())


def _current(request: Request, db: Session) -> tuple[LocalUser, LocalSession] | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    entry = db.get(LocalSession, hashlib.sha256(token.encode()).hexdigest())
    if entry is None or entry.expires_at <= int(time.time()):
        return None
    user = db.get(LocalUser, entry.user_id)
    return (user, entry) if user is not None else None


def _require_csrf(request: Request, session: LocalSession) -> None:
    _require_local_origin(request)
    actual = request.headers.get('x-csrf-token', '')
    if not actual or not hmac.compare_digest(actual, session.csrf_token):
        raise HTTPException(status_code=403, detail='Invalid anti-forgery token. Refresh the page and try again.')


def authenticated_subject(request: Request) -> str:
    with Session(engine) as db:
        active = _current(request, db)
        if active is None:
            raise HTTPException(status_code=401, detail='Sign in to your local account first.')
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            _require_csrf(request, active[1])
        return active[0].id


@router.get('/session')
def current_session(request: Request, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    with Session(engine) as db:
        active = _current(request, db)
        if active is None:
            return {'authenticated': False, 'user': None, 'csrf_token': None}
        user, session = active
        return {'authenticated': True, 'user': {'id': user.id, 'email': user.email},
                'csrf_token': session.csrf_token}


@router.post('/register', status_code=201)
def register(data: AuthCredentials, request: Request, response: Response):
    _require_local_origin(request)
    address = _normalized_email(data.email)
    _throttle(request, 'register:' + address)
    if len(data.password) < 12:
        raise HTTPException(status_code=422, detail='Use a password with at least 12 characters.')
    with Session(engine) as db:
        if db.scalar(select(LocalUser.id).where(LocalUser.email == address)):
            raise HTTPException(status_code=409, detail='This email already has an account. Sign in instead.')
        user = LocalUser(id=str(uuid.uuid4()), email=address,
                         password_hash=PASSWORD_HASHER.hash(data.password), created_at=_now())
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail='This email already has an account.')
        _create_session(db, user, response)
        return {'user': {'id': user.id, 'email': user.email}, 'mode': 'local_development'}


@router.post('/login')
def login(data: AuthCredentials, request: Request, response: Response):
    _require_local_origin(request)
    address = _normalized_email(data.email)
    _throttle(request, 'login:' + address)
    with Session(engine) as db:
        user = db.scalar(select(LocalUser).where(LocalUser.email == address))
        if user is None:
            # Keep response constant for non-existing and incorrect accounts.
            raise HTTPException(status_code=401, detail='Invalid email or password.')
        try:
            PASSWORD_HASHER.verify(user.password_hash, data.password)
        except (argon_errors.VerifyMismatchError, argon_errors.VerificationError, argon_errors.InvalidHashError):
            raise HTTPException(status_code=401, detail='Invalid email or password.')
        _create_session(db, user, response)
        return {'user': {'id': user.id, 'email': user.email}, 'mode': 'local_development'}


@router.post('/logout')
def logout(request: Request, response: Response):
    _require_local_origin(request)
    with Session(engine) as db:
        active = _current(request, db)
        if active:
            _require_csrf(request, active[1])
            db.delete(active[1]); db.commit()
    response.delete_cookie(key=SESSION_COOKIE, path='/', samesite='strict')
    return {'signed_out': True}


@router.post('/change-password')
def change_password(data: ChangePassword, request: Request):
    with Session(engine) as db:
        active = _current(request, db)
        if active is None:
            raise HTTPException(status_code=401, detail='Sign in first.')
        user, session = active
        _require_csrf(request, session)
        _throttle(request, 'password:' + user.id)
        try:
            PASSWORD_HASHER.verify(user.password_hash, data.current_password)
        except (argon_errors.VerifyMismatchError, argon_errors.VerificationError, argon_errors.InvalidHashError):
            raise HTTPException(status_code=401, detail='Current password is incorrect.')
        user.password_hash = PASSWORD_HASHER.hash(data.new_password)
        # Keep the current device signed in, revoke all other sessions for this user.
        db.execute(delete(LocalSession).where(LocalSession.user_id == user.id,
                                               LocalSession.token_hash != session.token_hash))
        db.commit()
        return {'password_changed': True, 'other_sessions_revoked': True}
