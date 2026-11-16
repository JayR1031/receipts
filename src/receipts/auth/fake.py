"""A stand-in identity provider for tests and local wiring (issue #41, ADR-0008).

`FakeIdentityProvider` satisfies `provider.IdentityProvider` without a network: each known
authorization code returns the claims configured for it, every call is recorded, and an unknown
code raises `AuthError("token_exchange")` as Google's token endpoint would refuse it. It is
chosen only by explicit injection (a test or the wiring passes it in); nothing selects it from
the process environment or the app's settings.

Synthetic values only: `fake-sub-0001`, `user@example.com`, `client-id-not-real`. The default
expiry is far in the future, so claims built here stay live under a real clock; pass `exp` to
test an expired token. A route test that needs the claims to carry the nonce of its own login
registers a code afterwards: `fake.claims_by_code[code] = fake_claims(nonce=nonce)`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from receipts.auth.models import AuthError, IdTokenClaims

FAKE_CODE: Final = "fake-code-0001"
FAKE_SUB: Final = "fake-sub-0001"
FAKE_EMAIL: Final = "user@example.com"
FAKE_CLIENT_ID: Final = "client-id-not-real"
FAKE_NONCE: Final = "fake-nonce-0001"
FAKE_ISSUER: Final = "https://accounts.google.com"
FAKE_EXP: Final = datetime(2100, 1, 1, tzinfo=UTC)


def fake_claims(
    *,
    sub: str = FAKE_SUB,
    email: str = FAKE_EMAIL,
    aud: str = FAKE_CLIENT_ID,
    nonce: str = FAKE_NONCE,
    iss: str = FAKE_ISSUER,
    exp: datetime = FAKE_EXP,
) -> IdTokenClaims:
    """Claims shaped like a valid Google ID token's, from synthetic defaults."""
    return IdTokenClaims(iss=iss, aud=aud, sub=sub, email=email, exp=exp, nonce=nonce)


@dataclass(frozen=True)
class ExchangeCall:
    """One call to `FakeIdentityProvider.exchange`, as it was made."""

    code: str
    redirect_uri: str
    code_verifier: str


class FakeIdentityProvider:
    """Returns configured claims per authorization code and records every exchange.

    `claims` is one claim set (answered for `FAKE_CODE` only) or a mapping from code to claims;
    with nothing given, `FAKE_CODE` answers `fake_claims()`. `claims_by_code` stays mutable so
    a test can add a code once it knows the nonce its login produced.
    """

    def __init__(self, claims: IdTokenClaims | Mapping[str, IdTokenClaims] | None = None) -> None:
        self.claims_by_code: dict[str, IdTokenClaims] = _by_code(claims)
        self.calls: list[ExchangeCall] = []

    async def exchange(self, code: str, *, redirect_uri: str, code_verifier: str) -> IdTokenClaims:
        self.calls.append(
            ExchangeCall(code=code, redirect_uri=redirect_uri, code_verifier=code_verifier)
        )
        claims = self.claims_by_code.get(code)
        if claims is None:
            raise AuthError("token_exchange")
        return claims


def _by_code(
    claims: IdTokenClaims | Mapping[str, IdTokenClaims] | None,
) -> dict[str, IdTokenClaims]:
    if claims is None:
        return {FAKE_CODE: fake_claims()}
    if isinstance(claims, IdTokenClaims):
        return {FAKE_CODE: claims}
    return dict(claims)
