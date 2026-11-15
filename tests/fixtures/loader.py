"""Load a synthetic comparison fixture as typed contract objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, TypeAdapter

from receipts.contracts import Claim, FetchedPage, SearchResult

COMPARISONS_DIR = Path(__file__).parent / "comparisons"


class Comparison(BaseModel):
    """The `comparison.json` file: who is compared with whom, in which category."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: str
    rival: str
    category: str


@dataclass(frozen=True)
class ComparisonFixture:
    subject: str
    rival: str
    category: str
    search_results: list[SearchResult]
    pages: list[FetchedPage]
    golden_claims: list[Claim]


def comparison_names() -> list[str]:
    return sorted(p.name for p in COMPARISONS_DIR.iterdir() if p.is_dir())


def load_comparison(name: str) -> ComparisonFixture:
    base = COMPARISONS_DIR / name
    meta = Comparison.model_validate_json((base / "comparison.json").read_text("utf-8"))
    results = TypeAdapter(list[SearchResult]).validate_json(
        (base / "search_results.json").read_text("utf-8")
    )
    pages = TypeAdapter(list[FetchedPage]).validate_json((base / "pages.json").read_text("utf-8"))
    claims = TypeAdapter(list[Claim]).validate_json(
        (base / "golden_claims.json").read_text("utf-8")
    )
    return ComparisonFixture(meta.subject, meta.rival, meta.category, results, pages, claims)
