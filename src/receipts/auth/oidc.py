"""The pure OpenID Connect pieces of "Sign in with Google" (issue #41, ADR-0008).

No network, no database, no clock: `now` is a parameter. The only side effect is randomness
from `secrets` for the state, the nonce and the PKCE verifier. The token exchange and the check
of the ID token's signature against Google's published keys live in the provider; this module
checks the claims once that signature is verified, builds the authorization URL and derives the
PKCE challenge (RFC 7636, S256) with the standard library.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime
from typing import Annotated, Final
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field

from receipts.auth.models import AuthError, IdTokenClaims

# Google issues either spelling (OpenID Connect discovery for accounts.google.com).
GOOGLE_ISSUERS: Final = frozenset({"https://accounts.google.com", "accounts.google.com"})
GOOGLE_AUTHORIZATION_ENDPOINT: Final = "https://accounts.google.com/o/oauth2/v2/auth"
SCOPE: Final = "openid email"
CALLBACK_PATH: Final = "/auth/callback"
# The local URI registered on the Google OAuth app; the deployed one is https://<host>/...
LOCAL_CALLBACK_URL: Final = "http://localhost:8000" + CALLBACK_PATH
_LOCAL_HOSTS: Final = frozenset({"localhost", "127.0.0.1"})
# 32 random bytes = 256 bits, which `token_urlsafe` writes as 43 URL-safe characters: the
# shortest verifier RFC 7636 allows, and the length its section 4.1 recommends.
_RANDOM_BYTES: Final = 32

NonEmpty = Annotated[str, Field(min_length=1)]


class OAuthRoundTrip(BaseModel):
    """One sign-in attempt's values, kept in the signed round-trip cookie until the callback."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: NonEmpty
    nonce: NonEmpty
    code_verifier: NonEmpty


def validate_claims(
    claims: IdTokenClaims, *, client_id: str, nonce: str, now: datetime
) -> IdTokenClaims:
    """Return `claims` unchanged if Google issued them to us, for this attempt, and they are live.

    Call it only after the token's signature is verified. Raises `AuthError` whose `check` is
    the first failed check: `iss`, `aud`, `exp` (expired when `exp <= now`) or `nonce` (equal
    to the one this attempt sent, never merely present). `now` is timezone-aware.
    """
    if claims.iss not in GOOGLE_ISSUERS:
        raise AuthError("iss")
    if not _same(client_id, claims.aud):
        raise AuthError("aud")
    if not claims.exp > now:
        raise AuthError("exp")
    if not _same(nonce, claims.nonce):
        raise AuthError("nonce")
    return claims


def _same(expected: str, received: str) -> bool:
    """Constant-time equality on UTF-8 bytes (`compare_digest` refuses non-ASCII `str`).

    An empty expected value never matches, so a lost nonce or client id cannot pass as equal.
    """
    return bool(expected) and secrets.compare_digest(expected.encode(), received.encode())


def callback_url(host: str) -> str:
    """The redirect URI for a request's `Host`: one of the two URIs registered with Google.

    A local host, with or without a port, gets the registered local URI exactly; any other host
    gets `https://<host>/auth/callback`. Google refuses a redirect URI it does not have
    registered, so a forged `Host` header ends the sign-in at Google rather than elsewhere.
    """
    name = host.partition(":")[0].lower()
    if name in _LOCAL_HOSTS:
        return LOCAL_CALLBACK_URL
    return f"https://{host}{CALLBACK_PATH}"


def new_code_verifier() -> str:
    """A fresh PKCE verifier: 43 URL-safe characters (RFC 7636 section 4.1)."""
    return secrets.token_urlsafe(_RANDOM_BYTES)


def code_challenge(verifier: str) -> str:
    """The S256 challenge: base64url of the verifier's SHA-256, without padding."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def new_state() -> str:
    """A fresh `state`, compared for equality on the callback to stop cross-site requests."""
    return secrets.token_urlsafe(_RANDOM_BYTES)


def new_nonce() -> str:
    """A fresh `nonce`, which Google copies into the ID token to stop a replayed token."""
    return secrets.token_urlsafe(_RANDOM_BYTES)


def new_round_trip() -> OAuthRoundTrip:
    """The state, nonce and PKCE verifier for one new sign-in attempt."""
    return OAuthRoundTrip(state=new_state(), nonce=new_nonce(), code_verifier=new_code_verifier())


def authorization_url(
    *, client_id: str, redirect_uri: str, state: str, nonce: str, code_challenge: str
) -> str:
    """Google's authorization endpoint with the authorization-code + PKCE request for `openid
    email`. Every value is form-encoded, so none can add or replace a parameter."""
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": SCOPE,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}"
