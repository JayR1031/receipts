"""The one `runs` table (scope cut 2026-11-14), in portable SQLAlchemy 2 types.

`JSON`, `String` and `DateTime` exist on both SQLite (unit tests) and Postgres (Neon), so the
same mapping runs in both. The `battlecard` and `events` columns hold the serialised
`Battlecard` and `list[RunEvent]` from `receipts.contracts`; the contracts, not the table, are
the source of truth for their shape.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

JsonObject = dict[str, object]


class UTCDateTime(TypeDecorator[datetime]):
    """A timezone-aware datetime that survives SQLite.

    Postgres keeps the offset in `timestamptz`; SQLite's `DateTime` drops it. Binding
    normalises to UTC, and reading attaches UTC to a naive value, so callers always see an
    aware datetime equal to the one they stored.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("runs.created_at must be timezone-aware")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Base(DeclarativeBase):
    pass


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    rival: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    battlecard: Mapped[JsonObject | None] = mapped_column(JSON, nullable=True)
    events: Mapped[list[JsonObject]] = mapped_column(JSON, nullable=False, default=list)
