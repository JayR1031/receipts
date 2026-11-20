"""Lane L2: the verifier evaluation (issue #59).

The first half runs `evaluate` on invented rows (every URL ends in `.example`). The second half is
the CI gate: it re-runs the Verifier on the committed, labeled set of real claims and fails when
precision or recall falls below the floors in `receipts.verify.evaluation`.
"""

from __future__ import annotations

import pytest

from receipts.contracts import Claim, FetchedPage, QuoteReceipt, SearchReceipt, SearchResult
from receipts.fakes import data
from receipts.verify.evaluation import (
    DATASET,
    EXCERPT_LIMIT,
    PRECISION_FLOOR,
    RECALL_FLOOR,
    EvalRow,
    Evidence,
    Label,
    Verdict,
    evaluate,
    load,
    rerun,
    stored_precision,
    wilson,
)

URL = "https://acme.example/pricing"
PAGE = FetchedPage(url=URL, text="Pro is $20 per seat. Team is $40.", fetched_at=data.T0, ok=True)


def _row(
    row_id: str,
    text: str,
    quote: str,
    label: Label,
    *,
    page: FetchedPage | None = PAGE,
    stage: str = "agent",
) -> EvalRow:
    claim = Claim(
        domain="pricing", about="subject", text=text, receipt=QuoteReceipt(url=URL, quote=quote)
    )
    verdict = rerun(
        EvalRow(
            id=row_id,
            run_id="run-x",
            subject="Acme",
            rival="Zeta",
            stage="agent",
            claim=claim,
            recorded=Verdict(verified=False),
            evidence=Evidence(page=page),
        )
    )
    return EvalRow.model_validate(
        {
            "id": row_id,
            "run_id": "run-x",
            "subject": "Acme",
            "rival": "Zeta",
            "stage": stage,
            "claim": claim,
            "recorded": verdict,
            "evidence": None if stage == "stored" else Evidence(page=page),
            "label": label,
        }
    )


def test_precision_counts_verified_claims_their_receipt_does_not_back() -> None:
    rows = [
        _row("a", "Pro is $20.", "Pro is $20 per seat", "supported"),
        _row("b", "Pro is $20 for every team.", "Pro is $20 per seat", "unsupported"),
        _row("c", "Team is $40.", "Team is $40", "supported"),
    ]
    report = evaluate(rows)
    assert (report.precision.hits, report.precision.total) == (2, 3)
    assert (report.recall.hits, report.recall.total) == (2, 2)
    assert report.false_verified_by_method["quote_exact"].hits == 1
    assert report.confusion == {("supported", True): 2, ("unsupported", True): 1}


def test_recall_counts_supported_claims_the_verifier_rejects() -> None:
    rows = [
        _row("a", "Pro is $20.", "Pro is $20 per seat", "supported"),
        _row("b", "Pro is $20.", "Pro is $25 per seat", "wrong"),
        _row("c", "Pro is $20.", "Pro is $20 per seat", "supported", page=None),
    ]
    report = evaluate(rows)
    assert (report.recall.hits, report.recall.total) == (1, 2)
    assert (report.precision.hits, report.precision.total) == (1, 1)


def test_stored_rows_are_not_rerun_and_count_apart() -> None:
    stored = _row("s", "Pro is $20 for every team.", "Pro is $20 per seat", "unsupported")
    stored = stored.model_copy(update={"stage": "stored", "evidence": None})
    report = evaluate([stored])
    assert report.rows == 0
    assert rerun(stored) == stored.recorded
    rate = stored_precision([stored])
    assert (rate.hits, rate.total) == (0, 1)


def test_a_search_row_is_rerun_against_its_logged_rows() -> None:
    receipt = SearchReceipt(query="acme pricing", rank=1, url=URL, ts=data.T0)
    claim = Claim(domain="positioning_seo", about="subject", text="Acme ranks 1.", receipt=receipt)
    logged = SearchResult(
        query="acme pricing", rank=1, url=URL, title="Acme", snippet="", ts=data.T0
    )
    row = EvalRow(
        id="s",
        run_id="run-x",
        subject="Acme",
        rival="Zeta",
        stage="agent",
        claim=claim,
        recorded=Verdict(verified=True, verify_method="search_log"),
        evidence=Evidence(rows=[logged]),
        label="supported",
    )
    assert rerun(row) == row.recorded
    assert rerun(row.model_copy(update={"evidence": Evidence(rows=[])})).verified is False


def test_wilson_interval_brackets_the_rate() -> None:
    low, high = wilson(96, 129)
    assert 0.66 < low < 96 / 129 < high < 0.82
    assert wilson(0, 0) == (0.0, 1.0)
    assert wilson(10, 10)[1] == 1.0


# --- the committed set: the CI gate ------------------------------------------------------------


@pytest.fixture(scope="module")
def committed() -> list[EvalRow]:
    return load(DATASET)


def test_every_committed_row_is_labeled_with_a_reason(committed: list[EvalRow]) -> None:
    assert len(committed) >= 150
    assert len({row.id for row in committed}) == len(committed)
    unlabeled = [row.id for row in committed if row.label is None or not row.label_reason]
    assert unlabeled == []


def test_committed_rows_keep_excerpts_not_whole_pages(committed: list[EvalRow]) -> None:
    pages = [row.evidence.page for row in committed if row.evidence and row.evidence.page]
    too_long = [page.url for page in pages if len(page.text) > EXCERPT_LIMIT]
    assert pages and too_long == []
    assert all(row.evidence is not None for row in committed if row.stage != "stored")


def test_a_draft_names_the_rewrite_that_replaced_it(committed: list[EvalRow]) -> None:
    ids = {row.id: row for row in committed}
    for row in committed:
        if row.stage == "draft":
            assert row.repaired_by in ids and ids[row.repaired_by].stage == "repair"


def test_verifier_precision_and_recall_stay_above_the_floors(committed: list[EvalRow]) -> None:
    report = evaluate(committed)
    assert report.precision.value >= PRECISION_FLOOR, (
        f"precision {report.precision.hits}/{report.precision.total} is below {PRECISION_FLOOR}"
    )
    assert report.recall.value >= RECALL_FLOOR, (
        f"recall {report.recall.hits}/{report.recall.total} is below {RECALL_FLOOR}"
    )
