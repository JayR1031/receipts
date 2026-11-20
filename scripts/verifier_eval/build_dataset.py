"""Build the committed evaluation set from `.eval-raw/` (issue #59). Local only.

Every claim of every recorded run becomes one row: the claims on the battlecard (`stage` `agent`
or, for a Mellea rewrite, `repair`), and each failing draft that a rewrite replaced (`draft`).
`--stored` adds the claims of finished runs on the live site (`stage` `stored`): no page text
was kept for those, so they carry the verdict the app gave and are reported apart.

The committed row keeps a short excerpt of the page, never the whole page: a window of raw text
around the best match for the quote, widened until the Verifier's result on the excerpt (verified,
method and note) is the same as on the full page. Search receipts keep only the rows logged for
their query.

Names: `.eval-raw/redact.txt` (gitignored; one name or username per line) lists strings to
replace with `[name]` in claim text, quotes, excerpts and search rows. The Verifier is run again
on the redacted row, and a row whose result changes is reported and left out.

Labels: an existing dataset's `label` and `label_reason` are carried over by row id, so a
rebuild keeps them.

Usage: uv run python scripts/verifier_eval/build_dataset.py [--stored URL]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from receipts.contracts import Battlecard, Claim, FetchedPage, QuoteReceipt, SearchResult
from receipts.verify import verify_claim
from receipts.verify.evaluation import DATASET, EvalRow, Evidence, Verdict, load

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / ".eval-raw"
REDACT = RAW / "redact.txt"
WINDOW = 700
REDACTED = "[name]"


def _verdict(claim: Claim) -> Verdict:
    return Verdict(
        verified=claim.verified, verify_method=claim.verify_method, verify_note=claim.verify_note
    )


def _bare(claim: Claim) -> Claim:
    return claim.model_copy(update={"verified": False, "verify_method": None, "verify_note": None})


def _check(claim: Claim, evidence: Evidence) -> Verdict:
    pages = {evidence.page.url: evidence.page} if evidence.page is not None else {}
    return _verdict(verify_claim(claim, pages, evidence.rows))


def _excerpt(claim: Claim, receipt: QuoteReceipt, page: FetchedPage, full: Verdict) -> FetchedPage:
    text = page.text
    alignment = fuzz.partial_ratio_alignment(receipt.quote.lower(), text.lower())
    start, end = (alignment.dest_start, alignment.dest_end) if alignment else (0, 0)
    width = WINDOW
    while True:
        lo, hi = max(0, start - width), min(len(text), end + width)
        cut = page.model_copy(update={"text": text[lo:hi]})
        if (lo == 0 and hi == len(text)) or _check(claim, Evidence(page=cut, rows=[])) == full:
            return cut
        width *= 2


def _evidence(
    claim: Claim, pages: dict[str, dict[str, Any]], rows: list[dict[str, Any]], full: Verdict
) -> Evidence:
    receipt = claim.receipt
    if isinstance(receipt, QuoteReceipt):
        raw = pages.get(receipt.url)
        if raw is None:
            return Evidence(page=None, rows=[])
        page = FetchedPage.model_validate(raw)
        return Evidence(page=_excerpt(claim, receipt, page, full), rows=[])
    logged = [SearchResult.model_validate(r) for r in rows if r["query"] == receipt.query]
    return Evidence(page=None, rows=logged)


def _redact(text: str, names: Sequence[str]) -> str:
    for name in names:
        text = re.sub(re.escape(name), REDACTED, text, flags=re.IGNORECASE)
    return text


def _redacted(row: EvalRow, names: Sequence[str]) -> EvalRow:
    if not names:
        return row
    raw = row.model_dump_json()
    for name in names:
        escaped = json.dumps(name)[1:-1]
        raw = re.sub(re.escape(escaped), REDACTED, raw, flags=re.IGNORECASE)
    return EvalRow.model_validate_json(raw)


def _key(claim: Claim) -> str:
    return json.dumps([claim.text, claim.receipt.model_dump(mode="json")], sort_keys=True)


def _recorded_rows(path: Path) -> list[EvalRow]:
    data = json.loads(path.read_text())
    card = Battlecard.model_validate(data["battlecard"])
    run = str(card.run_id)
    short = run.removeprefix("run-")[:8]
    rewrites = {
        _key(Claim.model_validate(r["rewrite"])): Claim.model_validate(r["draft"])
        for r in data["repairs"]
        if r["rewrite"] is not None
    }
    gave_up = {_key(Claim.model_validate(r["draft"])) for r in data["repairs"] if not r["rewrite"]}
    out: list[EvalRow] = []
    for n, claim in enumerate(card.claims, 1):
        domain = claim.domain
        pages, rows = data["pages"].get(domain, {}), data["rows"].get(domain, [])
        draft = rewrites.get(_key(claim))
        row_id = f"{short}-{n:02d}"
        full = _verdict(claim)
        out.append(
            EvalRow(
                id=row_id,
                run_id=run,
                subject=card.subject,
                rival=card.rival,
                stage="agent" if draft is None else "repair",
                repair_outcome="gave_up" if _key(claim) in gave_up else None,
                claim=_bare(claim),
                recorded=full,
                evidence=_evidence(claim, pages, rows, full),
            )
        )
        if draft is not None:
            pages_full = {u: FetchedPage.model_validate(p) for u, p in pages.items()}
            searched = [SearchResult.model_validate(r) for r in rows]
            draft_full = _verdict(verify_claim(draft, pages_full, searched))
            out.append(
                EvalRow(
                    id=f"{row_id}d",
                    run_id=run,
                    subject=card.subject,
                    rival=card.rival,
                    stage="draft",
                    repaired_by=row_id,
                    repair_outcome="rewritten",
                    claim=_bare(draft),
                    recorded=draft_full,
                    evidence=_evidence(draft, pages, rows, draft_full),
                )
            )
    return out


def _stored_rows(base: str, recorded_runs: set[str]) -> list[EvalRow]:
    with urllib.request.urlopen(f"{base}/api/runs", timeout=60) as resp:
        runs = json.load(resp)
    out: list[EvalRow] = []
    for summary in runs:
        if summary["status"] != "done" or summary["run_id"] in recorded_runs:
            continue
        with urllib.request.urlopen(f"{base}/api/runs/{summary['run_id']}", timeout=60) as resp:
            card = Battlecard.model_validate(json.load(resp))
        short = str(card.run_id).removeprefix("run-")[:8]
        out.extend(
            EvalRow(
                id=f"{short}-{n:02d}",
                run_id=str(card.run_id),
                subject=card.subject,
                rival=card.rival,
                stage="stored",
                claim=_bare(claim),
                recorded=_verdict(claim),
                evidence=None,
            )
            for n, claim in enumerate(card.claims, 1)
        )
    return out


def _names() -> list[str]:
    lines = REDACT.read_text().splitlines() if REDACT.exists() else []
    return [n.strip() for n in lines if n.strip() and not n.startswith("#")]


def _finish(rows: list[EvalRow], names: Sequence[str]) -> list[EvalRow]:
    """Redact, drop rows whose result redaction changes, and carry over existing labels."""
    old = {r.id: r for r in load(DATASET)} if DATASET.exists() else {}
    kept: list[EvalRow] = []
    for row in rows:
        clean = _redacted(row, names)
        if clean.evidence is not None and _check(clean.claim, clean.evidence) != clean.recorded:
            print(f"left out {row.id}: redaction changes the Verifier's result", file=sys.stderr)
            continue
        if clean.id in old:
            prior = old[clean.id]
            clean = clean.model_copy(
                update={"label": prior.label, "label_reason": prior.label_reason}
            )
        kept.append(clean)
    return kept


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--stored", metavar="URL", help="also add the live site's finished runs")
    args = parser.parse_args(argv)
    rows = [row for path in sorted(RAW.glob("run-*.json")) for row in _recorded_rows(path)]
    if args.stored:
        rows.extend(_stored_rows(args.stored.rstrip("/"), {r.run_id for r in rows}))
    kept = _finish(rows, _names())
    DATASET.parent.mkdir(parents=True, exist_ok=True)
    DATASET.write_text("".join(r.model_dump_json(exclude_none=True) + "\n" for r in kept))
    stages = Counter(row.stage for row in kept)
    print(f"{len(kept)} rows -> {DATASET.relative_to(ROOT)} {dict(stages)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
