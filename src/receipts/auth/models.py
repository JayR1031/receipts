"""Shared types for sign-in, sessions and run limits (lane L7, issue #41, ADR-0008).

Pure data: nothing here reads the environment, a database, the network or the clock.

Times. `IdTokenClaims.exp` and `SessionUser.expires_at` are compared with an injected clock, so
both are timezone-aware (`AwareDatetime`): a naive value fails when the model is built, not later
when a comparison with an aware `now` would raise. `exp` arrives as the JWT NumericDate (seconds
since the epoch) and pydantic parses it into an aware UTC datetime at the edge. `User.created_at`
is a stored record time and stays a plain `datetime`, like the contracts' timestamps.
"""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator


class _Frozen(BaseModel):
    """Immutable and rejects unknown fields, like `receipts.contracts`."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class User(_Frozen):
    """A person who signed in: our id, Google's subject id and email, nothing else."""

    id: str
    sub: str
    email: str
    created_at: datetime


class SessionUser(_Frozen):
    """What the session cookie carries: our user id and its expiry, never the email."""

    user_id: str
    expires_at: AwareDatetime


class IdTokenClaims(BaseModel):
    """The six claims `validate_claims` checks, parsed from Google's ID token at the edge.

    Other claims in the token (name, picture, ...) are dropped here (`extra="ignore"`), so nothing
    beyond `sub` and `email` can reach storage. A missing claim fails parsing, and so does an
    `aud` that is a list rather than the single string Google issues.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    iss: str
    aud: str
    sub: str
    email: str
    exp: AwareDatetime
    nonce: str


class StartDecision(_Frozen):
    """Whether a run may start. A refusal's reason carries its count, denominator and window,
    e.g. `5 of 5 runs used today (UTC)`; an allowed start has no reason."""

    allowed: bool
    reason: str | None = None

    @model_validator(mode="after")
    def _reason_matches_allowed(self) -> Self:
        if self.allowed and self.reason is not None:
            raise ValueError("an allowed start carries no reason")
        if not self.allowed and not (self.reason or "").strip():
            raise ValueError("a refused start says why")
        return self

    @classmethod
    def allow(cls) -> Self:
        return cls(allowed=True)

    @classmethod
    def refuse(cls, reason: str) -> Self:
        return cls(allowed=False, reason=reason)


class AccountStatus(_Frozen):
    """The account line: the signed-in email (or none), today's runs used and the limit that
    applies. The UI renders `f"{runs_used} of {runs_limit} runs used today (UTC)"` from it."""

    email: str | None
    runs_used: int
    runs_limit: int
    sign_in_available: bool


class AuthError(Exception):
    """A sign-in check failed; `check` names which one (`iss`, `aud`, `exp`, `nonce`, ...).

    The message carries the check's name only, never a token, a claim value or an email.
    """

    def __init__(self, check: str) -> None:
        self.check = check
        super().__init__(f"sign-in check failed: {check}")
