"""`SqlUserRepo`: the people who signed in with Google, over the `users` table (issue #41).

Same engine pattern as `SqlRunRepo` (`LazyEngine`): built lazily from `DATABASE_URL` or the
injected URL, or an injected `Engine`, so the wiring can share one pool between both repos. Every
method is `async` and runs the blocking SQLAlchemy call in a worker thread (`asyncio.to_thread`).

`get_or_create(sub, email, now)` is idempotent on `sub`, Google's stable subject id: every sign-in
after the first returns the first row's `User` unchanged, its `created_at` and its email included.
The email is not refreshed: the identity is `sub`, the email is shown on the account line only,
and a refresh would turn every sign-in into a write. A person whose Google address changes keeps
seeing the old one until the owner deletes the row (ADR-0008); accepted for this app.

Race: two first sign-ins with one `sub` (two tabs, a replayed callback) can both miss the lookup
and both insert. The UNIQUE on `users.sub` rejects the second insert with `IntegrityError`, and
that caller re-reads the winner's row, so both get the same `User` and one row exists.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from receipts.auth.models import User
from receipts.db.repo import LazyEngine
from receipts.db.schema import UserRow


def new_user_id() -> str:
    """Our id for a new user: `user-` and 32 hex digits, never derived from Google's `sub`."""
    return f"user-{uuid4().hex}"


def _user(row: UserRow) -> User:
    return User(id=row.id, sub=row.sub, email=row.email, created_at=row.created_at)


class SqlUserRepo(LazyEngine):
    """See the module docstring. `url=None` defers to `DATABASE_URL` on first use."""

    async def get_or_create(self, sub: str, email: str, now: datetime) -> User:
        """The user with this `sub`, created with `email` and `created_at=now` if there is none.
        `now` must be timezone-aware, like every stored time."""
        return await asyncio.to_thread(self._get_or_create, sub, email, now)

    def _get_or_create(self, sub: str, email: str, now: datetime) -> User:
        existing = self._by_sub(sub)
        if existing is not None:
            return existing
        try:
            return self._insert(sub, email, now)
        except IntegrityError:
            winner = self._by_sub(sub)  # a concurrent first sign-in inserted this `sub` first
            if winner is None:
                raise
            return winner

    def _by_sub(self, sub: str) -> User | None:
        with self._session() as session:
            row = session.scalars(select(UserRow).where(UserRow.sub == sub)).one_or_none()
        return None if row is None else _user(row)

    def _insert(self, sub: str, email: str, now: datetime) -> User:
        row = UserRow(id=new_user_id(), sub=sub, email=email, created_at=now)
        with self._session() as session, session.begin():
            session.add(row)
        return _user(row)

    async def get(self, user_id: str) -> User | None:
        """The user with our id `user_id`, or `None`."""
        return await asyncio.to_thread(self._get, user_id)

    def _get(self, user_id: str) -> User | None:
        with self._session() as session:
            row = session.get(UserRow, user_id)
        return None if row is None else _user(row)
