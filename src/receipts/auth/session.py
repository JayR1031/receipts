"""The two signed cookies of sign-in (issue #41, ADR-0008): the session and the OAuth round trip.

Both are compact JWTs signed with HS256 under `SESSION_SECRET` through joserfc. The session
carries our internal user id and its expiry, nothing else: no email, no Google token. The round
trip carries one sign-in attempt's state, nonce and PKCE verifier for ten minutes, so no
server-side session table is needed. Both are signed, not encrypted: the browser holding a
cookie can read it, which is why each carries only these values.

Verifying checks the signature first, with the algorithm pinned to HS256, then parses the claims
into a strict private model here at the edge (no claims `dict` leaves this module), then compares
the expiry with the injected, timezone-aware `now`: a token is expired when `exp <= now`. Any
failure is `None`; no exception escapes a verify call. `secret.get_secret_value()` is called
only inside `_sign` and `_verify`, and no error message here carries a secret or a claim.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Annotated, Final, Literal, TypedDict, TypeVar

from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import OctKey
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from receipts.auth.models import SessionUser
from receipts.auth.oidc import NonEmpty, OAuthRoundTrip

SESSION_TTL: Final = timedelta(days=7)
ROUND_TRIP_TTL: Final = timedelta(minutes=10)
SESSION_MAX_AGE: Final = int(SESSION_TTL.total_seconds())
ROUND_TRIP_MAX_AGE: Final = int(ROUND_TRIP_TTL.total_seconds())
SESSION_COOKIE: Final = "receipts_session"
ROUND_TRIP_COOKIE: Final = "receipts_oauth"


class CookieFlags(TypedDict):
    """The keyword arguments Starlette's `set_cookie` and `delete_cookie` take for both cookies."""

    path: str
    secure: bool
    httponly: bool
    samesite: Literal["lax", "strict", "none"]


# Lax, not Strict: Google's redirect back to /auth/callback is a cross-site top-level GET, and a
# Strict round-trip cookie would not be sent with it.
COOKIE_FLAGS: Final[CookieFlags] = {
    "path": "/",
    "secure": True,
    "httponly": True,
    "samesite": "lax",
}

_ALG: Final = "HS256"
# 9999-12-31T23:59:59Z: the last second `datetime` can hold, so a parsed `exp` always converts.
_LAST_EPOCH: Final = 253_402_300_799
_Epoch = Annotated[int, Field(strict=True, ge=1, le=_LAST_EPOCH)]


class _Claims(BaseModel):
    """A cookie's payload. Strict: an unknown claim, a missing one or a textual `exp` fails."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    exp: _Epoch


class _SessionClaims(_Claims):
    uid: NonEmpty


class _RoundTripClaims(_Claims):
    state: NonEmpty
    nonce: NonEmpty
    code_verifier: NonEmpty


_C = TypeVar("_C", bound=_Claims)


def _epoch(moment: datetime) -> int:
    """JWT NumericDate, floored to the second, so a token never outlives the time it was given."""
    return math.floor(moment.timestamp())


def _moment(epoch: int) -> datetime:
    return datetime.fromtimestamp(epoch, UTC)


def _sign(claims: _Claims, secret: SecretStr) -> str:
    """Raises `ValueError` for an empty secret (joserfc refuses an empty HMAC key)."""
    key = OctKey.import_key(secret.get_secret_value())
    return jwt.encode({"alg": _ALG}, claims.model_dump(), key, algorithms=[_ALG])


def _verify(token: str, secret: SecretStr, model: type[_C], now: datetime) -> _C | None:
    """The claims of an HS256 token we signed that has not expired at `now`; else `None`.

    `jwt.decode` checks the signature before it parses the payload; `model` then accepts only
    the claims of this kind of cookie. An empty secret verifies nothing, so it is `None` too.
    `TypeError` is caught because joserfc 1.8.0 raises it, not a `JoseError`, for some
    malformed headers (a `crit` that is not a list, a header that is a JSON list) before it
    checks the signature. pydantic's `ValidationError` is a `ValueError`.
    """
    try:
        key = OctKey.import_key(secret.get_secret_value())
        claims = model.model_validate(jwt.decode(token, key, algorithms=[_ALG]).claims)
    except (JoseError, ValueError, TypeError):
        return None
    if _moment(claims.exp) <= now:
        return None
    return claims


def new_session(user_id: str, *, now: datetime) -> SessionUser:
    """A session for `user_id` that ends `SESSION_TTL` after `now`, floored to the second, so
    it round-trips through the cookie unchanged."""
    return SessionUser(user_id=user_id, expires_at=_moment(_epoch(now + SESSION_TTL)))


def sign_session(user: SessionUser, *, secret: SecretStr) -> str:
    """The session cookie's value: our user id and the expiry (to the second), nothing else."""
    return _sign(_SessionClaims(uid=user.user_id, exp=_epoch(user.expires_at)), secret)


def verify_session(token: str, *, secret: SecretStr, now: datetime) -> SessionUser | None:
    """The signed-in user, or `None` for a tampered, expired, foreign or malformed cookie."""
    claims = _verify(token, secret, _SessionClaims, now)
    if claims is None:
        return None
    return SessionUser(user_id=claims.uid, expires_at=_moment(claims.exp))


def sign_round_trip(values: OAuthRoundTrip, *, secret: SecretStr, now: datetime) -> str:
    """The round-trip cookie's value: one attempt's values, expiring `ROUND_TRIP_TTL` after
    `now`."""
    claims = _RoundTripClaims(
        state=values.state,
        nonce=values.nonce,
        code_verifier=values.code_verifier,
        exp=_epoch(now + ROUND_TRIP_TTL),
    )
    return _sign(claims, secret)


def verify_round_trip(token: str, *, secret: SecretStr, now: datetime) -> OAuthRoundTrip | None:
    """The attempt's values, or `None` for a tampered, expired, foreign or malformed cookie."""
    claims = _verify(token, secret, _RoundTripClaims, now)
    if claims is None:
        return None
    return OAuthRoundTrip(
        state=claims.state, nonce=claims.nonce, code_verifier=claims.code_verifier
    )
