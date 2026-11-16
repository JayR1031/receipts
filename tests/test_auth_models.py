"""Issue #41 contract: the frozen auth types and the `Gate` protocol (ADR-0008).

Synthetic identities only: `fake-sub-0001`, addresses at example.com.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

import pytest
from pydantic import BaseModel, ValidationError
from starlette.requests import Request

from receipts.auth import (
    AccountStatus,
    AuthError,
    Gate,
    IdTokenClaims,
    SessionUser,
    StartDecision,
    User,
)
from receipts.contracts import RunId, RunRequest, RunSummary

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
CLAIMS = {
    "iss": "https://accounts.google.com",
    "aud": "fake-client-id.apps.example.com",
    "sub": "fake-sub-0001",
    "email": "person@example.com",
    "exp": int(NOW.timestamp()),
    "nonce": "fake-nonce-0001",
}

USER = User(id="u-0001", sub="fake-sub-0001", email="person@example.com", created_at=NOW)
SESSION = SessionUser(user_id="u-0001", expires_at=NOW + timedelta(days=7))
ACCOUNT = AccountStatus(
    email="person@example.com", runs_used=3, runs_limit=5, sign_in_available=True
)


@pytest.mark.parametrize(
    ("model", "field", "value"),
    [
        (USER, "email", "other@example.com"),
        (SESSION, "user_id", "u-0002"),
        (IdTokenClaims.model_validate(CLAIMS), "nonce", "other-nonce"),
        (StartDecision.allow(), "allowed", False),
        (ACCOUNT, "runs_used", 0),
    ],
)
def test_every_auth_model_is_frozen(model: BaseModel, field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        setattr(model, field, value)


def test_start_decision_allow_has_no_reason() -> None:
    decision = StartDecision.allow()
    assert decision.allowed is True
    assert decision.reason is None


def test_start_decision_refuse_keeps_its_text() -> None:
    decision = StartDecision.refuse("3 of 5 runs used today (UTC)")
    assert decision.allowed is False
    assert decision.reason == "3 of 5 runs used today (UTC)"


@pytest.mark.parametrize(
    ("allowed", "reason"),
    [(True, "3 of 5 runs used today (UTC)"), (False, None), (False, "")],
)
def test_start_decision_rejects_a_reason_that_does_not_match(
    allowed: bool, reason: str | None
) -> None:
    """An allowed start carries no reason; a refusal always says why."""
    with pytest.raises(ValidationError):
        StartDecision(allowed=allowed, reason=reason)


def test_auth_error_names_the_failed_check() -> None:
    error = AuthError("nonce")
    assert isinstance(error, Exception)
    assert error.check == "nonce"
    assert "nonce" in str(error)


def test_id_token_claims_parse_numeric_exp_and_drop_other_claims() -> None:
    """The token's JSON is parsed at the edge; profile claims beyond the six are not kept."""
    claims = IdTokenClaims.model_validate(
        {**CLAIMS, "email_verified": True, "name": "Not Kept", "picture": "https://x.example"}
    )
    assert claims.exp == NOW
    assert claims.exp.tzinfo is not None
    assert set(claims.model_dump()) == {"iss", "aud", "sub", "email", "exp", "nonce"}


@pytest.mark.parametrize("missing", ["iss", "aud", "sub", "email", "exp", "nonce"])
def test_id_token_claims_require_every_checked_claim(missing: str) -> None:
    with pytest.raises(ValidationError):
        IdTokenClaims.model_validate({k: v for k, v in CLAIMS.items() if k != missing})


def test_id_token_claims_reject_a_naive_exp() -> None:
    """`exp` is compared with an aware clock; a naive datetime would raise there instead."""
    with pytest.raises(ValidationError):
        IdTokenClaims.model_validate({**CLAIMS, "exp": datetime(2026, 11, 15, 12, 0)})


def test_gate_is_a_protocol_with_the_four_methods() -> None:
    assert Protocol in Gate.__mro__
    public = {name for name in vars(Gate) if not name.startswith("_")}
    assert public == {"identify", "start", "history", "account"}


class _StubGate:
    """Satisfies `Gate` structurally; pyright checks the assignment in the test below."""

    def identify(self, request: Request) -> SessionUser | None:
        return None

    async def start(self, request: RunRequest, passcode: str, user: SessionUser | None) -> RunId:
        return RunId("run-0001")

    async def history(self, user: SessionUser | None) -> list[RunSummary]:
        return []

    async def account(self, user: SessionUser | None) -> AccountStatus:
        return AccountStatus(email=None, runs_used=0, runs_limit=20, sign_in_available=False)


async def test_a_structural_stub_satisfies_gate() -> None:
    gate: Gate = _StubGate()
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    assert gate.identify(request) is None
    run_request = RunRequest(subject="Acme", rival="Globex")
    assert await gate.start(run_request, "", None) == RunId("run-0001")
    assert await gate.history(None) == []
    assert (await gate.account(None)).runs_limit == 20
