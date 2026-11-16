"""Lane L4: SQLAlchemy 2 persistence over the `runs` and `users` tables. Owned by L4 from W1.

W2 wiring: `SqlRunRepo()` reads `DATABASE_URL` on first use (or `SqlRunRepo(url=...)`), and
`await create_schema(repo.engine)` creates the tables (and adds `runs.user_id` to an existing
Postgres `runs` table). Issue #41: `SqlUserRepo(engine=repo.engine)` shares that engine for
sign-in. Nothing here runs at import.
"""

from receipts.db.repo import SqlRunRepo, create_schema, make_engine
from receipts.db.schema import Base, RunRow, UserRow
from receipts.db.users import SqlUserRepo

__all__ = [
    "Base",
    "RunRow",
    "SqlRunRepo",
    "SqlUserRepo",
    "UserRow",
    "create_schema",
    "make_engine",
]
