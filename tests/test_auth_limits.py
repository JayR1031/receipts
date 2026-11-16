"""The `may_start` table (issue #41): who may start a run, and the refusal's count and window."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from receipts.auth.limits import may_start
from receipts.auth.models import SessionUser

USER = SessionUser(user_id="user-test-1", expires_at=datetime(2030, 1, 1, tzinfo=UTC))
LIMIT, CAP = 5, 20
RESET = "the limit resets at 00:00 UTC"
USER_REFUSAL = f"5 of 5 runs used today (UTC); {RESET}"
CAP_REFUSAL = f"20 of 20 signed-out runs used today (UTC); {RESET}"
PASSCODE_REFUSAL = "a valid passcode is required"

# (signed in, passcode_ok, user_runs, signed_out_runs, allowed, reason)
CASES = [
    pytest.param(True, True, 0, 0, True, None, id="signed-in-under-limit"),
    pytest.param(True, False, 0, 0, True, None, id="signed-in-wrong-passcode-allowed"),
    pytest.param(True, False, 4, 0, True, None, id="signed-in-4-of-5"),
    pytest.param(True, True, 5, 0, False, USER_REFUSAL, id="signed-in-5-of-5"),
    pytest.param(True, True, 7, 0, False, "7 of 5 runs used today (UTC); " + RESET, id="over"),
    pytest.param(True, False, 0, 20, True, None, id="signed-in-ignores-full-signed-out-cap"),
    pytest.param(False, False, 0, 0, False, PASSCODE_REFUSAL, id="signed-out-no-passcode"),
    pytest.param(False, False, 3, 25, False, PASSCODE_REFUSAL, id="signed-out-no-passcode-busy"),
    pytest.param(False, True, 0, 0, True, None, id="signed-out-passcode-under-cap"),
    pytest.param(False, True, 0, 19, True, None, id="signed-out-19-of-20"),
    pytest.param(False, True, 0, 20, False, CAP_REFUSAL, id="signed-out-20-of-20"),
    pytest.param(False, True, 5, 0, True, None, id="signed-out-ignores-user-count"),
]


@pytest.mark.parametrize(
    ("signed_in", "passcode_ok", "user_runs", "out_runs", "allowed", "reason"), CASES
)
def test_may_start(
    signed_in: bool,
    passcode_ok: bool,
    user_runs: int,
    out_runs: int,
    allowed: bool,
    reason: str | None,
) -> None:
    decision = may_start(USER if signed_in else None, passcode_ok, user_runs, out_runs, LIMIT, CAP)
    assert decision.allowed is allowed
    assert decision.reason == reason


@pytest.mark.parametrize(
    ("signed_in", "passcode_ok", "user_runs", "out_runs"),
    [(True, True, 5, 0), (True, False, 9, 0), (False, False, 0, 0), (False, True, 0, 20)],
)
def test_refusals_say_why_and_never_say_limit_reached(
    signed_in: bool, passcode_ok: bool, user_runs: int, out_runs: int
) -> None:
    decision = may_start(USER if signed_in else None, passcode_ok, user_runs, out_runs, LIMIT, CAP)
    assert not decision.allowed
    assert decision.reason is not None and decision.reason.strip()
    assert "limit reached" not in decision.reason
