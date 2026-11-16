"""The start rule (issue #41, ADR-0008): pure, no clock, settings, database or network.

Signed in: no passcode, counted against that user's daily limit. Signed out: a correct passcode
and room under the signed-out daily cap. A passcode never makes a visitor a signed-in user.
"""

from __future__ import annotations

from receipts.auth.models import SessionUser, StartDecision

_RESET = "the limit resets at 00:00 UTC"


def _signed_in(used: int, limit: int) -> StartDecision:
    if used < limit:
        return StartDecision.allow()
    return StartDecision.refuse(f"{used} of {limit} runs used today (UTC); {_RESET}")


def _signed_out(passcode_ok: bool, used: int, cap: int) -> StartDecision:
    if not passcode_ok:
        return StartDecision.refuse("a valid passcode is required")
    if used < cap:
        return StartDecision.allow()
    return StartDecision.refuse(f"{used} of {cap} signed-out runs used today (UTC); {_RESET}")


def may_start(
    user: SessionUser | None,
    passcode_ok: bool,
    user_runs_today: int,
    signed_out_runs_today: int,
    per_user_limit: int,
    signed_out_cap: int,
) -> StartDecision:
    """Decide whether a run may start; each branch reads only its own count."""
    if user is not None:
        return _signed_in(user_runs_today, per_user_limit)
    return _signed_out(passcode_ok, signed_out_runs_today, signed_out_cap)
