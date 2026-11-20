"""Record live runs for the verifier evaluation (issue #59). Local only: never in CI.

Runs each pair through the real service (Anthropic, Keenable, Mellea repairs) over a temporary
SQLite file, never the Neon database. Two wrappers record what a stored run does not keep:

- the Verifier wrapper saves every page and search row each claim was checked against, per
  domain, so `build_dataset.py` can re-run the Verifier on exactly what the run saw;
- the repairer wrapper saves each failing draft next to Mellea's rewrite (or `None`).

Writes one JSON file per run to `.eval-raw/` (gitignored: full page text stays on this machine).
Reads `ANTHROPIC_API_KEY` and `KEENABLE_API_KEY` from the environment.

Usage: uv run python scripts/verifier_eval/record.py [--pair "Subject|Rival|category" ...]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from receipts.api.wiring import build_live_service
from receipts.contracts import Claim, DomainPack, FetchedPage, RunRequest, SearchResult
from receipts.db import SqlRunRepo, create_schema
from receipts.harness.live import live_repair_factory
from receipts.harness.repair import ClaimRepairer, RepairRequest
from receipts.settings import get_settings
from receipts.verify import verify_claim

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / ".eval-raw"
PAIRS: tuple[tuple[str, str, str], ...] = (
    ("Notion", "Coda", "docs and wikis"),
    ("Figma", "Sketch", "design tools"),
    ("Vercel", "Netlify", "frontend hosting"),
    ("Slack", "Microsoft Teams", "team chat"),
    ("Duolingo", "Babbel", "language learning"),
    ("Canva", "Adobe Express", "online design"),
)


class Recorder:
    def __init__(self) -> None:
        self.pages: dict[str, dict[str, FetchedPage]] = {}
        self.rows: dict[str, dict[tuple[str, int, str], SearchResult]] = {}
        self.repairs: list[dict[str, Any]] = []

    def verify(
        self, claim: Claim, pages: Mapping[str, FetchedPage], rows: Sequence[SearchResult]
    ) -> Claim:
        self.pages.setdefault(claim.domain, {}).update(pages)
        logged = self.rows.setdefault(claim.domain, {})
        for row in rows:
            logged[(row.query, row.rank, row.url)] = row
        return verify_claim(claim, pages, rows)

    def repair_factory(self, pack: DomainPack) -> ClaimRepairer:
        inner = live_repair_factory(pack)

        async def repair(request: RepairRequest) -> Claim | None:
            rewrite = await inner(request)
            self.repairs.append(
                {
                    "domain": pack.id,
                    "draft": request.claim.model_dump(mode="json"),
                    "failure": request.failure,
                    "rewrite": None if rewrite is None else rewrite.model_dump(mode="json"),
                }
            )
            return rewrite

        return repair

    def dump(self) -> dict[str, Any]:
        return {
            "pages": {
                domain: {url: page.model_dump(mode="json") for url, page in pages.items()}
                for domain, pages in self.pages.items()
            },
            "rows": {
                domain: [row.model_dump(mode="json") for row in rows.values()]
                for domain, rows in self.rows.items()
            },
            "repairs": self.repairs,
        }


async def record(subject: str, rival: str, category: str, db: Path) -> Path:
    get_settings.cache_clear()
    recorder = Recorder()
    repo = SqlRunRepo(url=f"sqlite:///{db}")
    await create_schema(repo.engine)
    service = build_live_service(
        get_settings(), repo=repo, verify=recorder.verify, repair_factory=recorder.repair_factory
    )
    started = time.monotonic()
    run_id = await service.start(RunRequest(subject=subject, rival=rival, category=category))
    async for _event in service.events(run_id):
        pass
    await service.wait(run_id)
    card = await service.get(run_id)
    if card is None:
        raise RuntimeError(f"{run_id}: no battlecard stored")
    RAW.mkdir(exist_ok=True)
    out = RAW / f"{run_id}.json"
    out.write_text(
        json.dumps({"battlecard": card.model_dump(mode="json"), **recorder.dump()}, indent=1)
    )
    wall = time.monotonic() - started
    print(f"{run_id} {subject} vs {rival}: {card.verified_count}/{card.total_count} {wall:.0f}s")
    return out


async def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--pair", action="append", help='"Subject|Rival|category"')
    args = parser.parse_args(argv)
    pairs = [tuple(p.split("|", 2)) for p in args.pair] if args.pair else list(PAIRS)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (subject, rival, category) in enumerate(pairs):
            await record(subject, rival, category, Path(tmp) / f"run{i}.db")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
