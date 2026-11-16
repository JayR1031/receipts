"""The identity-provider edge of "Sign in with Google" (issue #41, ADR-0008).

`IdentityProvider` is the one thing the auth routes need: swap an authorization code for the
claims of a Google ID token whose RS256 signature has been verified. The claims are **not yet
checked against this attempt**: the caller passes them to `oidc.validate_claims` with its client
id, the round trip's nonce and an injected `now`. A verified signature proves only that Google
issued the token, not that it was issued to us, for this attempt, or that it is still live. The
split keeps the clock and the nonce in the route, which owns both, and lets the route's tests
drive `validate_claims` through `FakeIdentityProvider` (`auth/fake.py`).

`GoogleIdentityProvider.exchange`, in order:

1. POST the code, the redirect URI, the PKCE verifier and the client credentials to Google's
   token endpoint, and parse the 2xx JSON body into `TokenResponse` (only `id_token` is kept;
   the access token is dropped at parse and never stored).
2. Read the ID token's `kid` from its protected header (a non-empty string is required).
3. Fetch Google's published key set (JWKS) unless the cache already holds that `kid`.
4. Verify the compact JWS with joserfc, the algorithm pinned to RS256, against RSA keys only,
   then parse the claims into `IdTokenClaims` here, so no claims `dict` leaves this module.

Key cache: the provider instance keeps the last key set it fetched and fetches again only when
a token names a `kid` the cache does not hold; the new set replaces the old one, so a key Google
has withdrawn is dropped at the next refetch. `Cache-Control` is not read, and the cache lives
as long as the instance: a provider built per request fetches once per sign-in. The ID token
arrives from Google over TLS in reply to our authenticated request, so a caller cannot choose
the `kid` and force refetches.

Errors: every failure is an `AuthError` whose `check` names the step: `token_exchange` (a
network error, a non-2xx status, a body that is not JSON or has no `id_token`), `jwks` (the key
set cannot be fetched or holds no usable RSA key) or `id_token` (a malformed token, a missing or
unknown `kid`, a bad signature, an algorithm other than RS256, or claims that do not parse).
Each is raised after its `except` block has ended, so it chains no exception: a pydantic
`ValidationError` quotes its input, which here would be a token or an email. `TypeError` is
caught with joserfc's own errors because joserfc 1.8.0 raises it for some malformed headers (a
`crit` that is not a list of strings) before it checks the signature.

Secrets: `client_secret.get_secret_value()` is called once, inside the token request's form
body, and nothing here logs. Both requests carry a 10 second timeout. Nothing here reads the
process environment or the app's settings: the routes and the wiring build the provider.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Final, Protocol, TypeVar

import httpx
from joserfc import jws, jwt
from joserfc.errors import JoseError
from joserfc.jwk import DictKey, Key, KeySet, RSAKey
from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError

from receipts.auth.models import AuthError, IdTokenClaims
from receipts.auth.oidc import NonEmpty

TOKEN_ENDPOINT: Final = "https://oauth2.googleapis.com/token"
JWKS_URL: Final = "https://www.googleapis.com/oauth2/v3/certs"
HTTP_TIMEOUT: Final = 10.0
ID_TOKEN_ALG: Final = "RS256"


class IdentityProvider(Protocol):
    """Swaps an authorization code for the signature-verified claims of an ID token."""

    async def exchange(self, code: str, *, redirect_uri: str, code_verifier: str) -> IdTokenClaims:
        """The ID token's claims, signature verified but not yet checked against this attempt:
        pass them to `validate_claims` before trusting them. Raises `AuthError` on any failure,
        with `check` set to `token_exchange`, `jwks` or `id_token`."""
        ...


class TokenResponse(BaseModel):
    """The token endpoint's reply, reduced to the ID token. Every other field is dropped."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id_token: NonEmpty


class _KeySetBody(BaseModel):
    """A JWKS document: a list of keys whose values are strings or lists of strings."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    keys: list[DictKey]


class _Header(BaseModel):
    """The one header field read before verification: which of Google's keys signed it."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    kid: NonEmpty


_M = TypeVar("_M", bound=BaseModel)


class GoogleIdentityProvider:
    """The real provider: Google's token endpoint and published keys, over `httpx`.

    `http` is for tests (an `httpx.AsyncClient` on a `MockTransport`); the provider never closes
    a client it was given. Without one it opens a client per exchange and closes it after.
    """

    def __init__(
        self, client_id: str, client_secret: SecretStr, *, http: httpx.AsyncClient | None = None
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http
        self._keys: KeySet | None = None

    async def exchange(self, code: str, *, redirect_uri: str, code_verifier: str) -> IdTokenClaims:
        async with self._client() as client:
            id_token = await self._post_token(
                client, code, redirect_uri=redirect_uri, code_verifier=code_verifier
            )
            keys = await self._keys_for(client, _kid(id_token))
        return _decode(id_token, keys)

    @asynccontextmanager
    async def _client(self) -> AsyncGenerator[httpx.AsyncClient, None]:
        if self._http is not None:
            yield self._http
            return
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            yield client

    async def _post_token(
        self, client: httpx.AsyncClient, code: str, *, redirect_uri: str, code_verifier: str
    ) -> str:
        """The ID token from Google's reply to the authorization-code grant (RFC 6749 4.1.3,
        with the PKCE verifier of RFC 7636 4.5)."""
        try:
            response = await client.post(
                TOKEN_ENDPOINT,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret.get_secret_value(),
                },
                timeout=HTTP_TIMEOUT,
            )
        except httpx.HTTPError:
            response = None
        token = _parse(response, TokenResponse)
        if token is None:
            raise AuthError("token_exchange")
        return token.id_token

    async def _keys_for(self, client: httpx.AsyncClient, kid: str) -> KeySet:
        """The cached key set if it holds `kid`; otherwise Google's current set, which replaces
        the cache. A `kid` still missing after the refetch fails in `_decode`."""
        if self._keys is None or not _holds(self._keys, kid):
            self._keys = await _fetch_jwks(client)
        return self._keys


async def _fetch_jwks(client: httpx.AsyncClient) -> KeySet:
    try:
        response = await client.get(JWKS_URL, timeout=HTTP_TIMEOUT)
    except httpx.HTTPError:
        response = None
    body = _parse(response, _KeySetBody)
    keys = None if body is None else _rsa_keys(body)
    if keys is None:
        raise AuthError("jwks")
    return keys


def _parse(response: httpx.Response | None, model: type[_M]) -> _M | None:
    """A 2xx response's JSON body as `model`; `None` for no response, any other status, or a
    body that is not JSON of that shape."""
    if response is None or not response.is_success:
        return None
    try:
        return model.model_validate_json(response.content)
    except ValidationError:
        return None


def _rsa_keys(body: _KeySetBody) -> KeySet | None:
    """The RSA keys of a JWKS; `None` if a key is malformed or none is RSA. Google publishes
    RSA keys only, and RS256 is the only algorithm `_decode` accepts."""
    try:
        imported = KeySet.import_key_set({"keys": body.keys})
    except (JoseError, ValueError, TypeError):
        return None
    rsa: list[Key] = [key for key in imported if isinstance(key, RSAKey)]
    return KeySet(rsa) if rsa else None


def _holds(keys: KeySet, kid: str) -> bool:
    return any(key.kid == kid for key in keys)


def _kid(id_token: str) -> str:
    """The `kid` of the token's protected header, read without verifying anything yet."""
    try:
        header = _Header.model_validate(jws.extract_compact(id_token.encode()).protected)
    except (JoseError, ValueError, TypeError):
        header = None
    if header is None:
        raise AuthError("id_token")
    return header.kid


def _decode(id_token: str, keys: KeySet) -> IdTokenClaims:
    """The claims of an RS256 token signed by a key in `keys`. joserfc checks the signature
    before it parses the payload; pydantic's `ValidationError` is a `ValueError`."""
    try:
        token = jwt.decode(id_token, keys, algorithms=[ID_TOKEN_ALG])
        claims = IdTokenClaims.model_validate(token.claims)
    except (JoseError, ValueError, TypeError):
        claims = None
    if claims is None:
        raise AuthError("id_token")
    return claims
