"""How often the Verifier is right, measured on a labeled set of real claims (issue #59).

Each `EvalRow` is one claim from a real run, the evidence the run saw (a page excerpt or the
search rows logged for its query), the Verifier's result at the time, and a human label:

- `supported`: the receipt really backs the claim text;
- `unsupported`: the quote or search row exists, but it does not say what the claim says;
- `wrong`: the receipt does not match the page or the search log.

`evaluate` re-runs `verify_claim` on every row with evidence, so a rule change moves the numbers.
Rows with `stage` `stored` (finished runs whose page text was never kept) carry the verdict the
app gave and are counted apart. The dataset lives at `DATASET`, a path inside a repository
checkout; `docs/verifier-eval.md` is the labeling guide and records the baseline.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from receipts.contracts import Claim, Domain, FetchedPage, SearchResult, VerifyMethod
from receipts.verify.rules import verify_claim

DATASET = Path(__file__).resolve().parents[3] / "tests" / "data" / "verifier_eval" / "claims.jsonl"

PRECISION_FLOOR = 0.72
"""CI fails below this: the 2026-11-20 baseline, 96 of 129 (0.744), minus about two points."""
RECALL_FLOOR = 0.97
"""CI fails below this: the 2026-11-20 baseline, 96 of 97 (0.990), minus about two points."""
EXCERPT_LIMIT = 4000
"""The longest page excerpt a committed row may carry: rows keep excerpts, never whole pages."""

Label = Literal["supported", "unsupported", "wrong"]
Stage = Literal["agent", "repair", "draft", "stored"]
RepairOutcome = Literal["rewritten", "gave_up"]


class _Row(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Verdict(_Row):
    verified: bool
    verify_method: VerifyMethod | None = None
    verify_note: str | None = None


class Evidence(_Row):
    page: FetchedPage | None = None
    rows: list[SearchResult] = []


class EvalRow(_Row):
    id: str
    run_id: str
    subject: str
    rival: str
    stage: Stage
    """`agent`: the agent's claim, as shown. `repair`: a Mellea rewrite, as shown. `draft`: a
    failing draft that the rewrite `repaired_by` replaced. `stored`: from a run with no
    evidence kept."""
    repaired_by: str | None = None
    repair_outcome: RepairOutcome | None = None
    """`rewritten` on a draft Mellea replaced; `gave_up` on a failing claim it could not fix."""
    claim: Claim
    recorded: Verdict
    evidence: Evidence | None = None
    label: Label | None = None
    label_reason: str | None = None


def load(path: Path = DATASET) -> list[EvalRow]:
    return [EvalRow.model_validate_json(line) for line in path.read_text().splitlines() if line]


def rerun(row: EvalRow) -> Verdict:
    """The Verifier's result on the row's evidence today; the recorded one for `stored` rows."""
    if row.evidence is None:
        return row.recorded
    page = row.evidence.page
    pages = {page.url: page} if page is not None else {}
    checked = verify_claim(row.claim, pages, row.evidence.rows)
    return Verdict(
        verified=checked.verified,
        verify_method=checked.verify_method,
        verify_note=checked.verify_note,
    )


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """The Wilson score interval for a proportion (95% by default); `(0, 1)` when `total` is 0."""
    if total == 0:
        return 0.0, 1.0
    p = successes / total
    centre = p + z * z / (2 * total)
    spread = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    denom = 1 + z * z / total
    return max(0.0, (centre - spread) / denom), min(1.0, (centre + spread) / denom)


@dataclass(frozen=True)
class Rate:
    hits: int
    total: int

    @property
    def value(self) -> float:
        return self.hits / self.total if self.total else 0.0

    @property
    def interval(self) -> tuple[float, float]:
        return wilson(self.hits, self.total)


@dataclass(frozen=True)
class Report:
    rows: int
    confusion: dict[tuple[Label, bool], int]
    """(label, verified) -> count."""
    precision: Rate
    """Of the claims verified, the share labeled `supported`: the headline number."""
    recall: Rate
    """Of the `supported` claims, the share verified."""
    false_verified_by_method: dict[VerifyMethod, Rate]
    """Per method: of the claims verified that way, the share not labeled `supported`."""
    false_verified_by_domain: dict[Domain, Rate]
    rewritten: Rate
    """Of the failing claims sent to Mellea, the share it rewrote into one that verifies."""
    rewrites_supported: Rate
    """Of Mellea's rewrites, the share labeled `supported`."""
    changed: list[str] = field(default_factory=list[str])
    """Ids whose verdict today differs from the recorded one (a rule changed since)."""


def evaluate(rows: Iterable[EvalRow]) -> Report:
    """Precision, recall and their splits over the labeled rows that have evidence."""
    labeled = [r for r in rows if r.label is not None and r.evidence is not None]
    verdicts = {r.id: rerun(r) for r in labeled}
    confusion: dict[tuple[Label, bool], int] = {}
    for r in labeled:
        key = (r.label, verdicts[r.id].verified)
        confusion[key] = confusion.get(key, 0) + 1  # type: ignore[index]
    verified = [r for r in labeled if verdicts[r.id].verified]
    supported = [r for r in labeled if r.label == "supported"]

    def _false(group: Sequence[EvalRow]) -> Rate:
        return Rate(sum(r.label != "supported" for r in group), len(group))

    methods: dict[VerifyMethod, list[EvalRow]] = {}
    domains: dict[Domain, list[EvalRow]] = {}
    for r in verified:
        method = verdicts[r.id].verify_method
        if method is not None:
            methods.setdefault(method, []).append(r)
        domains.setdefault(r.claim.domain, []).append(r)
    repairs = [r for r in labeled if r.stage == "repair"]
    sent = [r for r in labeled if r.repair_outcome is not None]
    return Report(
        rows=len(labeled),
        confusion=confusion,
        precision=Rate(sum(r.label == "supported" for r in verified), len(verified)),
        recall=Rate(sum(verdicts[r.id].verified for r in supported), len(supported)),
        false_verified_by_method={m: _false(g) for m, g in sorted(methods.items())},
        false_verified_by_domain={d: _false(g) for d, g in sorted(domains.items())},
        rewritten=Rate(sum(r.repair_outcome == "rewritten" for r in sent), len(sent)),
        rewrites_supported=Rate(sum(r.label == "supported" for r in repairs), len(repairs)),
        changed=[r.id for r in labeled if verdicts[r.id] != r.recorded],
    )


def stored_precision(rows: Iterable[EvalRow]) -> Rate:
    """Precision of the app's own verdicts on `stored` rows (not re-run: no evidence was kept)."""
    stored = [r for r in rows if r.stage == "stored" and r.label is not None]
    verified = [r for r in stored if r.recorded.verified]
    return Rate(sum(r.label == "supported" for r in verified), len(verified))
