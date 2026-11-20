"""L1: the Mellea repair loop for specialist claims (GitHub issue #39). No network.

The agent is `fake_llm`, the tools are `FakeKeenable`, the Verifier is L2's real `verify_claim`,
and Mellea runs its own instruct-validate-repair loop over a scripted backend (Mellea's
`DummyBackend`, recording the prompt it is given). Mellea only proposes a rewritten claim; the
Verifier alone decides `verified`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from mellea.backends.dummy import DummyBackend
from mellea.core import (
    BaseModelSubclass,
    C,
    CBlock,
    Component,
    Context,
    GenerateLog,
    ModelOutputThunk,
)
from mellea.formatters import TemplateFormatter

from receipts.contracts import (
    Claim,
    ClaimEvent,
    DomainPack,
    DoneEvent,
    DroppedEvent,
    FetchedPage,
    QuoteReceipt,
    RunEvent,
    RunId,
    RunRequest,
    SearchResult,
    VerifiedEvent,
)
from receipts.fakes import FakeKeenable, data, fake_llm
from receipts.harness import (
    Coordinator,
    SpecialistRunner,
    ToolLog,
    Verify,
    parse_claims,
    passthrough_verify,
)
from receipts.harness.repair import (
    MAX_REPAIRS,
    ClaimRepairer,
    MelleaClaimRepairer,
    RepairFactory,
    RepairRequest,
    evidence_for,
)
from receipts.verify import verify_claim

RUN_ID = RunId("run-repair-0001")
REQUEST = RunRequest(subject="Acme Widgets", rival="Zeta Gadgets", category="widgets")

GOOD_QUOTE = "Plans start at 9 dollars per seat"  # on data.SUBJECT_PAGE
MONTHLY_QUOTE = "Plans start at 9 dollars per seat per month"  # on it too: a different receipt
BAD_QUOTE = "Seats cost nine dollars monthly"  # not on it
STILL_BAD_QUOTE = "Seats are 9 dollars a month"  # not on it either


class RecordingBackend(DummyBackend):
    """Mellea's scripted backend, keeping the rendered prompt of every generation.

    It also attaches a `GenerateLog` to each output, as Mellea's real backends do: in Mellea
    0.9.0 the sampling loop asserts `result._generate_log is not None`, and the stock
    `DummyBackend` leaves it unset.
    """

    def __init__(self, responses: list[str]) -> None:
        super().__init__(responses)
        self.prompts: list[str] = []

    async def _generate_from_context(
        self,
        action: Component[C] | CBlock | ModelOutputThunk,
        ctx: Context,
        *,
        format: type[BaseModelSubclass] | None = None,
        model_options: dict[str, object] | None = None,
        tool_calls: bool = False,
    ) -> tuple[ModelOutputThunk[C], Context]:
        self.prompts.append(TemplateFormatter(model_id="dummy").print(action))
        output, new_ctx = await super()._generate_from_context(
            action, ctx, format=format, model_options=model_options, tool_calls=tool_calls
        )
        output._generate_log = GenerateLog()
        return output, new_ctx


def _fetch_call(url: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "keenable_fetch", "args": {"url": url}, "id": "f1", "type": "tool_call"}
        ],
    )


def _draft(quote: str, *, text: str = "Acme starts at 9 dollars per seat.") -> dict[str, object]:
    return {
        "about": "subject",
        "text": text,
        "receipt": {"kind": "quote", "url": data.SUBJECT_URL, "quote": quote},
    }


def _block(*drafts: dict[str, object]) -> str:
    return "```json\n" + json.dumps(list(drafts)) + "\n```"


def _agent(*drafts: dict[str, object]) -> list[str | AIMessage]:
    return [_fetch_call(data.SUBJECT_URL), "Here are the claims.\n" + _block(*drafts)]


def _runner(
    keenable: FakeKeenable,
    agent: list[str | AIMessage],
    backend: DummyBackend | None,
    *,
    verify: Verify = verify_claim,
    repair_factory: RepairFactory | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> SpecialistRunner:
    if repair_factory is None and backend is not None:
        scripted = backend

        def scripted_repairs(_pack: DomainPack) -> ClaimRepairer:
            return MelleaClaimRepairer(lambda: scripted)

        repair_factory = scripted_repairs
    return SpecialistRunner(
        keenable,
        keenable,
        model_factory=lambda _pack: fake_llm(agent),
        verify=verify,
        repair_factory=repair_factory,
        monotonic=monotonic,
    )


def _note(quote: str) -> str:
    claim = Claim(
        domain="pricing",
        about="subject",
        text="x",
        receipt=QuoteReceipt(url=data.SUBJECT_URL, quote=quote),
    )
    note = verify_claim(claim, data.sample_pages(), []).verify_note
    assert note is not None
    return note


async def _events(runner: SpecialistRunner, pack: DomainPack) -> list[RunEvent]:
    return [e async for e in runner.run(RUN_ID, REQUEST, pack)]


# --- a failing claim is repaired within budget, then verified by the real Verifier -----------


async def test_failing_claim_is_repaired_with_the_verifier_reason_then_verified(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    already_good = _draft(MONTHLY_QUOTE, text="Acme plans start at 9 dollars per seat.")
    backend = RecordingBackend([_block(_draft(STILL_BAD_QUOTE)), _block(_draft(GOOD_QUOTE))])
    runner = _runner(fake_keenable, _agent(already_good, _draft(BAD_QUOTE)), backend)

    events = await _events(runner, sample_pack)

    verified = [e.claim for e in events if isinstance(e, VerifiedEvent)]
    assert [c.receipt.quote for c in verified if isinstance(c.receipt, QuoteReceipt)] == [
        MONTHLY_QUOTE,
        GOOD_QUOTE,
    ]
    assert all(c.verify_method == "quote_exact" for c in verified)
    assert not [e for e in events if isinstance(e, DroppedEvent)]
    # Only the failing claim went to Mellea: two generations, no more.
    assert len(backend.prompts) == 2
    first, second = backend.prompts
    assert _note(BAD_QUOTE) in first  # the Verifier's own reason is the feedback
    assert data.SUBJECT_PAGE in first  # the fetched page is the grounding context
    assert "The following requirements failed before" in second  # Mellea's repair step
    assert _note(STILL_BAD_QUOTE) in second


async def test_search_receipt_is_repaired_against_the_logged_rows(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    def search_draft(rank: int) -> dict[str, object]:
        receipt = {"kind": "search", "query": "acme widgets pricing", "rank": rank}
        return {
            "about": "subject",
            "text": "Acme ranks for its pricing query.",
            "receipt": {**receipt, "url": data.SUBJECT_URL},
        }

    search_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "keenable_search",
                "args": {"query": "acme widgets pricing"},
                "id": "s1",
                "type": "tool_call",
            }
        ],
    )
    agent: list[str | AIMessage] = [search_call, _block(search_draft(3))]
    backend = RecordingBackend([_block(search_draft(1))])

    events = await _events(_runner(fake_keenable, agent, backend), sample_pack)

    assert [e.claim.verify_method for e in events if isinstance(e, VerifiedEvent)] == ["search_log"]
    assert f'"rank": 1, "url": "{data.SUBJECT_URL}"' in backend.prompts[0]


# --- a claim that cannot be repaired is still dropped, unchanged, and counted -----------------


async def test_unrepairable_claim_is_dropped_unchanged_and_counted(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    backend = RecordingBackend(["no json here at all", _block(_draft(STILL_BAD_QUOTE))])
    runner = _runner(fake_keenable, _agent(_draft(BAD_QUOTE)), backend)
    coordinator = Coordinator([sample_pack], runner, max_concurrent=1)

    events = [e async for e in coordinator.run(RUN_ID, REQUEST)]

    dropped = [e for e in events if isinstance(e, DroppedEvent)]
    assert len(dropped) == 1
    receipt = dropped[0].claim.receipt
    assert isinstance(receipt, QuoteReceipt) and receipt.quote == BAD_QUOTE  # the original
    assert dropped[0].reason == _note(BAD_QUOTE)
    done = events[-1]
    assert isinstance(done, DoneEvent)
    assert (done.verified_count, done.total_count) == (0, 1)
    assert "not one claim in a fenced json block" in backend.prompts[1]


# --- a repair may not copy another claim's receipt (GitHub issue #45) --------------------------

REPAIR_LOGGER = "receipts.harness.specialist"


def _quotes(claims: Sequence[Claim]) -> list[str]:
    return [c.receipt.quote for c in claims if isinstance(c.receipt, QuoteReceipt)]


def _repair_lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == REPAIR_LOGGER]


async def _coordinated(runner: SpecialistRunner, pack: DomainPack) -> list[RunEvent]:
    coordinator = Coordinator([pack], runner, max_concurrent=1)
    return [e async for e in coordinator.run(RUN_ID, REQUEST)]


def _counts(events: Sequence[RunEvent]) -> tuple[int, int]:
    done = events[-1]
    assert isinstance(done, DoneEvent)
    return done.verified_count, done.total_count


async def test_a_repair_that_duplicates_another_claims_receipt_is_not_accepted(
    fake_keenable: FakeKeenable, sample_pack: DomainPack, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=REPAIR_LOGGER)
    already_good = _draft(GOOD_QUOTE, text="Acme plans start at 9 dollars per seat.")
    backend = RecordingBackend([_block(_draft(GOOD_QUOTE))])  # passes Mellea's own check
    runner = _runner(fake_keenable, _agent(already_good, _draft(BAD_QUOTE)), backend)

    events = await _coordinated(runner, sample_pack)

    verified = [e.claim for e in events if isinstance(e, VerifiedEvent)]
    assert _quotes(verified) == [GOOD_QUOTE]
    assert [c.text for c in verified] == ["Acme plans start at 9 dollars per seat."]
    dropped = [e for e in events if isinstance(e, DroppedEvent)]
    assert _quotes([d.claim for d in dropped]) == [BAD_QUOTE]  # the original, unchanged
    assert [d.reason for d in dropped] == [_note(BAD_QUOTE)]
    assert _counts(events) == (1, 2)
    assert len(backend.prompts) == 1  # Mellea accepted the repair; the runner refused it
    assert _repair_lines(caplog) == ["claim repair: pricing failing=1 repaired=0"]


async def test_two_repairs_converging_on_one_receipt_keep_only_the_first(
    fake_keenable: FakeKeenable, sample_pack: DomainPack, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=REPAIR_LOGGER)
    backend = RecordingBackend([_block(_draft(GOOD_QUOTE))] * 2)
    agent = _agent(_draft(BAD_QUOTE), _draft(STILL_BAD_QUOTE))

    events = await _coordinated(_runner(fake_keenable, agent, backend), sample_pack)

    # Settled in the claims' order: the first repair takes GOOD_QUOTE, the second would copy it.
    claimed = [e.claim for e in events if isinstance(e, ClaimEvent)]
    assert _quotes(claimed) == [GOOD_QUOTE, STILL_BAD_QUOTE]
    assert _quotes([e.claim for e in events if isinstance(e, VerifiedEvent)]) == [GOOD_QUOTE]
    dropped = [e for e in events if isinstance(e, DroppedEvent)]
    assert [d.reason for d in dropped] == [_note(STILL_BAD_QUOTE)]
    assert _counts(events) == (1, 2)
    assert len(backend.prompts) == 2
    assert _repair_lines(caplog) == ["claim repair: pricing failing=2 repaired=1"]


async def test_a_repair_that_keeps_its_own_receipt_is_accepted(
    fake_keenable: FakeKeenable, sample_pack: DomainPack, caplog: pytest.LogCaptureFixture
) -> None:
    """The agent wrote two claims on GOOD_QUOTE; the second states a price the quote lacks. Its
    repair keeps that claim's own receipt and changes only the text, so it is accepted, though the
    first claim cites the same receipt: the receipt is the agent's, not a copy. A third claim's
    repair onto GOOD_QUOTE is still refused, so the duplicate check is live in this run."""
    caplog.set_level(logging.INFO, logger=REPAIR_LOGGER)
    fixed_text = "Acme plans start at 9 dollars per seat."
    wrong_price = _draft(GOOD_QUOTE, text="Acme starts at $12 per seat.")
    backend = RecordingBackend([_block(_draft(GOOD_QUOTE, text=fixed_text))] * 2)
    agent = _agent(_draft(GOOD_QUOTE), wrong_price, _draft(BAD_QUOTE))

    events = await _coordinated(_runner(fake_keenable, agent, backend), sample_pack)

    verified = [e.claim for e in events if isinstance(e, VerifiedEvent)]
    assert [c.text for c in verified] == ["Acme starts at 9 dollars per seat.", fixed_text]
    assert _quotes(verified) == [GOOD_QUOTE, GOOD_QUOTE]
    dropped = [e for e in events if isinstance(e, DroppedEvent)]
    assert _quotes([d.claim for d in dropped]) == [BAD_QUOTE]
    assert _counts(events) == (2, 3)
    assert _repair_lines(caplog) == ["claim repair: pricing failing=2 repaired=1"]


@pytest.mark.parametrize("repairs", [False, True], ids=["no-repair-factory", "no-failing-claim"])
async def test_agent_written_claims_sharing_a_quote_both_count(
    fake_keenable: FakeKeenable, sample_pack: DomainPack, repairs: bool
) -> None:
    backend = RecordingBackend([])
    first = _draft(GOOD_QUOTE)
    second = _draft(GOOD_QUOTE, text="Acme plans start at 9 dollars per seat.")
    runner = _runner(fake_keenable, _agent(first, second), backend if repairs else None)

    events = await _coordinated(runner, sample_pack)

    assert _quotes([e.claim for e in events if isinstance(e, VerifiedEvent)]) == [
        GOOD_QUOTE,
        GOOD_QUOTE,
    ]
    assert _counts(events) == (2, 2)
    assert backend.prompts == []


async def test_repair_budget_is_two_generations_per_claim(sample_pack: DomainPack) -> None:
    assert MAX_REPAIRS == 2
    backend = RecordingBackend([_block(_draft(STILL_BAD_QUOTE))] * 5 + [_block(_draft(GOOD_QUOTE))])
    claim = _claim(BAD_QUOTE)

    repaired = await MelleaClaimRepairer(lambda: backend)(_request(claim, sample_pack))

    assert repaired is None
    assert len(backend.prompts) == MAX_REPAIRS


# --- Mellea can never set `verified` -----------------------------------------------------------


async def test_repaired_claim_comes_back_unverified_even_if_the_model_says_verified(
    sample_pack: DomainPack,
) -> None:
    lying = {**_draft(GOOD_QUOTE), "verified": True, "verify_method": "quote_exact"}
    backend = RecordingBackend([_block(lying)])

    repaired = await MelleaClaimRepairer(lambda: backend)(_request(_claim(BAD_QUOTE), sample_pack))

    assert repaired is not None
    assert (repaired.verified, repaired.verify_method, repaired.verify_note) == (False, None, None)


async def test_a_repair_cannot_change_whom_the_claim_is_about(sample_pack: DomainPack) -> None:
    flipped = {**_draft(GOOD_QUOTE), "about": "rival"}
    backend = RecordingBackend([_block(flipped)])

    repaired = await MelleaClaimRepairer(lambda: backend)(_request(_claim(BAD_QUOTE), sample_pack))

    assert repaired is not None and repaired.about == "subject"


async def test_only_the_verifier_can_mark_a_repaired_claim_verified(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    """A repairer that hands back `verified=True` gets nowhere: with a Verifier that never
    verifies (`passthrough_verify` returns the claim as given), the claim is dropped."""

    class Cheat:
        async def __call__(self, request: RepairRequest) -> Claim:
            return request.claim.model_copy(
                update={"verified": True, "verify_method": "quote_exact", "verify_note": None}
            )

    cheat: ClaimRepairer = Cheat()
    runner = _runner(
        fake_keenable,
        _agent(_draft(BAD_QUOTE)),
        None,
        verify=passthrough_verify,
        repair_factory=lambda _pack: cheat,
    )

    events = await _events(runner, sample_pack)

    assert not [e for e in events if isinstance(e, VerifiedEvent)]
    dropped = [e.claim for e in events if isinstance(e, DroppedEvent)]
    assert [c.verified for c in dropped] == [False]
    assert [e.claim.verified for e in events if isinstance(e, ClaimEvent)] == [False]


# --- the pack's time budget, and a repairer that fails ----------------------------------------


async def test_no_repair_once_the_pack_time_budget_is_spent(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    """No time left: no repairer is built at all (so no LiteLLM backend), not merely cut off."""
    ticks = iter([0.0, float(sample_pack.timeout_s) + 1.0])
    backend = RecordingBackend([_block(_draft(GOOD_QUOTE))])
    built: list[str] = []

    def counting_factory(pack: DomainPack) -> ClaimRepairer:
        built.append(pack.id)
        return MelleaClaimRepairer(lambda: backend)

    runner = _runner(
        fake_keenable,
        _agent(_draft(BAD_QUOTE)),
        None,
        repair_factory=counting_factory,
        monotonic=lambda: next(ticks),
    )

    events = await _events(runner, sample_pack)

    assert built == []
    assert backend.prompts == []
    assert len([e for e in events if isinstance(e, DroppedEvent)]) == 1


async def test_a_slow_repair_is_cut_at_the_pack_deadline(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    budget = float(sample_pack.timeout_s)
    ticks = iter([0.0, budget - 0.05])  # 50 ms left when the repairs start

    class Slow:
        async def __call__(self, request: RepairRequest) -> Claim | None:
            await asyncio.sleep(30)
            return None

    slow: ClaimRepairer = Slow()
    runner = _runner(
        fake_keenable,
        _agent(_draft(BAD_QUOTE)),
        None,
        repair_factory=lambda _pack: slow,
        monotonic=lambda: next(ticks),
    )

    events = await asyncio.wait_for(_events(runner, sample_pack), timeout=5)

    assert len([e for e in events if isinstance(e, DroppedEvent)]) == 1


async def test_a_repairer_that_raises_leaves_the_claim_to_the_verifier(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    class Broken:
        async def __call__(self, request: RepairRequest) -> Claim | None:
            raise RuntimeError("backend unavailable")

    broken: ClaimRepairer = Broken()
    runner = _runner(
        fake_keenable, _agent(_draft(BAD_QUOTE)), None, repair_factory=lambda _pack: broken
    )

    events = await _events(runner, sample_pack)

    dropped = [e for e in events if isinstance(e, DroppedEvent)]
    assert [d.reason for d in dropped] == [_note(BAD_QUOTE)]


# --- blocking work stays off the event loop (Render's 5-second health check) ------------------


async def test_the_agent_build_and_the_verifier_run_off_the_event_loop(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    loop_thread = threading.get_ident()
    model_threads: list[int] = []
    verify_threads: list[int] = []

    def model_factory(_pack: DomainPack) -> BaseChatModel:
        model_threads.append(threading.get_ident())
        return fake_llm(_agent(_draft(GOOD_QUOTE), _draft(BAD_QUOTE)))

    def verify(
        claim: Claim, pages: Mapping[str, FetchedPage], rows: Sequence[SearchResult]
    ) -> Claim:
        verify_threads.append(threading.get_ident())
        return verify_claim(claim, pages, rows)

    runner = SpecialistRunner(
        fake_keenable, fake_keenable, model_factory=model_factory, verify=verify
    )

    events = await _events(runner, sample_pack)

    assert len([e for e in events if isinstance(e, VerifiedEvent)]) == 1
    assert model_threads and loop_thread not in model_threads
    assert len(verify_threads) == 2 and loop_thread not in verify_threads


async def test_the_repair_backend_is_built_off_the_event_loop(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    loop_thread = threading.get_ident()
    backend = RecordingBackend([_block(_draft(GOOD_QUOTE))])
    backend_threads: list[int] = []

    def build_backend() -> DummyBackend:
        backend_threads.append(threading.get_ident())
        return backend

    runner = _runner(
        fake_keenable,
        _agent(_draft(BAD_QUOTE)),
        None,
        repair_factory=lambda _pack: MelleaClaimRepairer(build_backend),
    )

    events = await _events(runner, sample_pack)

    assert len([e for e in events if isinstance(e, VerifiedEvent)]) == 1
    assert backend_threads and loop_thread not in backend_threads


# --- evidence and the live backend (no network) ------------------------------------------------


def test_evidence_is_the_cited_page_or_every_good_page_when_the_url_was_not_fetched() -> None:
    pages = data.sample_pages()
    cited = evidence_for(_claim(BAD_QUOTE), pages, [])
    assert list(cited) == [data.SUBJECT_URL]
    elsewhere = _claim(BAD_QUOTE).model_copy(
        update={"receipt": QuoteReceipt(url="https://unfetched.example/", quote=BAD_QUOTE)}
    )
    assert sorted(evidence_for(elsewhere, pages, [])) == sorted(pages)


def test_live_backend_is_litellm_to_anthropic_and_offline_at_import(
    monkeypatch: pytest.MonkeyPatch, sample_pack: DomainPack
) -> None:
    from receipts.harness.live import litellm_backend

    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "placeholder")
    monkeypatch.delenv("LITELLM_LOCAL_MODEL_COST_MAP")
    backend = litellm_backend(sample_pack.model)
    assert backend.model_id == f"anthropic/{sample_pack.model}"
    assert os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] == "True"


def test_app_import_and_create_app_load_neither_mellea_nor_litellm() -> None:
    root = Path(__file__).resolve().parents[1]
    code = (
        "import sys; from receipts.api.app import create_app; create_app(); "
        "print(sorted(m for m in ('mellea', 'litellm') if m in sys.modules))"
    )
    env = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"]}
    proc = subprocess.run(
        ["uv", "run", "--no-sync", "python", "-c", code],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines()[-1] == "[]"


# --- helpers for the direct repairer tests -----------------------------------------------------


def _claim(quote: str) -> Claim:
    return Claim(
        domain="pricing",
        about="subject",
        text="Acme starts at 9 dollars per seat.",
        receipt=QuoteReceipt(url=data.SUBJECT_URL, quote=quote),
    )


def _request(claim: Claim, pack: DomainPack) -> RepairRequest:
    pages: Mapping[str, FetchedPage] = data.sample_pages()
    rows: Sequence[SearchResult] = []
    log = ToolLog(fetches=list(pages.values()))
    return RepairRequest(
        claim=claim,
        failure=verify_claim(claim, pages, rows).verify_note or "",
        evidence=evidence_for(claim, pages, rows),
        check=lambda c: verify_claim(c, pages, rows),
        parse=lambda text: parse_claims(text, pack, log, data.T0),
    )
