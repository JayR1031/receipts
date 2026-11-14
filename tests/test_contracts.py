"""W0 contracts: typed, frozen, discriminated on `kind`. One test per acceptance bullet."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from receipts.contracts import (
    RUN_EVENT_ADAPTER,
    Claim,
    DomainPack,
    QuoteReceipt,
    RunEvent,
)

TS = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


def test_every_event_kind_round_trips_unchanged(sample_events: list[RunEvent]) -> None:
    kinds = {event.kind for event in sample_events}
    assert kinds == {
        "started",
        "search",
        "fetch",
        "claim",
        "verified",
        "dropped",
        "done",
        "error",
    }
    for event in sample_events:
        raw = RUN_EVENT_ADAPTER.dump_json(event)
        assert RUN_EVENT_ADAPTER.validate_json(raw) == event


def test_unknown_event_kind_is_rejected() -> None:
    payload = b'{"kind": "mystery", "run_id": "r1", "ts": "2026-11-14T12:00:00Z", "domain": null}'
    with pytest.raises(ValidationError) as excinfo:
        RUN_EVENT_ADAPTER.validate_json(payload)
    # The discriminator fails on the tag itself, not on each member in turn.
    assert excinfo.value.errors()[0]["type"] == "union_tag_invalid"


def test_unknown_receipt_kind_is_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        Claim.model_validate(
            {
                "domain": "pricing",
                "about": "rival",
                "text": "x",
                "receipt": {"kind": "rumor", "url": "https://a.example/", "quote": "x"},
                "verified": False,
                "verify_method": None,
                "verify_note": None,
            }
        )
    assert excinfo.value.errors()[0]["type"] == "union_tag_invalid"


def test_claim_rejects_an_extra_field() -> None:
    receipt = QuoteReceipt(url="https://a.example/p", quote="costs 9")
    with pytest.raises(ValidationError):
        Claim.model_validate(
            {
                "domain": "pricing",
                "about": "rival",
                "text": "costs 9",
                "receipt": receipt.model_dump(),
                "verified": False,
                "verify_method": None,
                "verify_note": None,
                "confidence": 0.9,
            }
        )


def test_domain_pack_applies_budget_defaults(sample_pack: DomainPack) -> None:
    assert sample_pack.max_searches == 3
    assert sample_pack.max_fetches == 4
