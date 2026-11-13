"""Interactive LOCAL-ONLY account recovery for developers who have Docker access.

Usage (from project root):
  docker compose exec backend env GUESTLIFT_ALLOW_LOCAL_PASSWORD_RESET=1 python -m app.dev_reset_password

Do not use this capability on a shared or public deployment.
"""
from __future__ import annotations

import os
from getpass import getpass
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from .local_auth import LocalSession, LocalUser, PASSWORD_HASHER
from .database import engine


def main() -> None:
    if os.getenv('GUESTLIFT_ALLOW_LOCAL_PASSWORD_RESET') != '1':
        raise SystemExit('Developer console reset disabled. Set GUESTLIFT_ALLOW_LOCAL_PASSWORD_RESET=1 explicitly.')
    address = input('Local account email: ').strip().casefold()
    with Session(engine) as db:
        user = db.scalar(select(LocalUser).where(LocalUser.email == address))
        if user is None:
            raise SystemExit('Local account not found; nothing changed.')
        password = getpass('New password (12+ characters): ')
        confirm = getpass('Confirm new password: ')
        if len(password) < 12 or len(password) > 128 or password != confirm:
            raise SystemExit('Password invalid or confirmation does not match; nothing changed.')
        user.password_hash = PASSWORD_HASHER.hash(password)
        db.execute(delete(LocalSession).where(LocalSession.user_id == user.id))
        db.commit()
        print('Password changed. All existing sessions revoked; sign in again.')


if __name__ == '__main__':
    main()
