"""Lane L4: SQLAlchemy 2 persistence (`SqlRunRepo`) over one `runs` table. Owned by L4 from W1.

W2 wiring: `SqlRunRepo()` reads `DATABASE_URL` on first use (or `SqlRunRepo(url=...)`), and
`await create_schema(repo.engine)` creates the table. Nothing here runs at import.
"""

from receipts.db.repo import SqlRunRepo, create_schema, make_engine
from receipts.db.schema import Base, RunRow

__all__ = ["Base", "RunRow", "SqlRunRepo", "create_schema", "make_engine"]
