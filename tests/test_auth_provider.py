"""Issue #41 `provider`: Google's token exchange and the ID token's signature check (ADR-0008).

No network: every request goes to an `httpx.MockTransport` that plays Google's token endpoint
and published key set. Synthetic values only: `fake-sub-0001`, `user@example.com`,
`client-id-not-real`, a client secret that exists only in this file, and RSA keys generated
here once per module.
"""

from __future__ import annotations

import base64
import inspect
import json
import re
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import ModuleType
from urllib.parse import parse_qs

import httpx
import pytest
from joserfc import jws, jwt
from joserfc.jwk import OctKey, RSAKey
from pydantic import SecretStr

import receipts.auth.fake as fake_module
import receipts.auth.provider as provider_module
from receipts.auth.fake import (
    FAKE_CLIENT_ID,
    FAKE_CODE,
    FAKE_EMAIL,
    FAKE_SUB,
    ExchangeCall,
    FakeIdentityProvider,
    fake_claims,
)
from receipts.auth.models import AuthError, IdTokenClaims
from receipts.auth.provider import (
    HTTP_TIMEOUT,
    JWKS_URL,
    TOKEN_ENDPOINT,
    GoogleIdentityProvider,
    IdentityProvider,
    TokenResponse,
)

CLIENT_ID = "client-id-not-real"
# Distinctive, so a search of any error text for it cannot match by accident.
SECRET_VALUE = "synthetic-client-secret-Qx7Zk2-not-real"
SECRET = SecretStr(SECRET_VALUE)
CODE = "fake-code-0001"
REDIRECT_URI = "http://localhost:8000/auth/callback"
VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
KID = "fake-kid-0001"
ROTATED_KID = "fake-kid-0002"
EMAIL = "user@example.com"
NONCE = "fake-nonce-0001"
ACCESS_TOKEN = "synthetic-access-token-not-stored"
EXP_AT = datetime(2026, 11, 15, 12, 5, tzinfo=UTC)
EXP = int(EXP_AT.timestamp())
CLAIMS: dict[str, object] = {
    "iss": "https://accounts.google.com",
    "aud": CLIENT_ID,
    "sub": "fake-sub-0001",
    "email": EMAIL,
    "email_verified": True,
    "exp": EXP,
    "iat": EXP - 3600,
    "nonce": NONCE,
    "picture": "https://example.com/synthetic.png",
}
ENVIRONMENT_READ = re.compile(r"os\.environ|getenv|get_settings|receipts\.settings|import os")


# --- builders --------------------------------------------------------------------------------


def _encode(data: object) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def _id_token(
    key: RSAKey, claims: dict[str, object] | None = None, *, kid: str = KID, alg: str = "RS256"
) -> str:
    header: dict[str, object] = {"alg": alg, "kid": kid}
    return jwt.encode(header, claims or CLAIMS, key, algorithms=[alg])


def _unsigned(header: object, claims: object = CLAIMS) -> str:
    """A token with a hand-made header and a signature nobody computed."""
    return _encode(header) + "." + _encode(claims) + ".AAAA"


def _without(name: str) -> dict[str, object]:
    return {key: value for key, value in CLAIMS.items() if key != name}


def _without_alg(key: RSAKey) -> RSAKey:
    """The same key pair with no `alg` parameter, so it can sign with another RSA algorithm."""
    data = {name: value for name, value in key.as_dict(private=True).items() if name != "alg"}
    return RSAKey.import_key(data)


def _tampered(token: str) -> str:
    """Keep the header and signature; swap in a payload that names another user."""
    header, _, signature = token.split(".")
    return ".".join([header, _encode({**CLAIMS, "sub": "fake-sub-0002"}), signature])


# --- a stand-in for Google's two endpoints ----------------------------------------------------


@dataclass
class Reply:
    status: int
    body: bytes

    def response(self) -> httpx.Response:
        return httpx.Response(
            self.status, content=self.body, headers={"content-type": "application/json"}
        )


def _json(data: object, status: int = 200) -> Reply:
    return Reply(status, json.dumps(data).encode())


def _token_reply(id_token: object) -> Reply:
    return _json({"id_token": id_token, "access_token": ACCESS_TOKEN, "token_type": "Bearer"})


def _jwks_reply(*keys: RSAKey) -> Reply:
    return _json({"keys": [key.as_dict(private=False) for key in keys]})


@dataclass
class FakeGoogle:
    """Answers the token endpoint and the key set URL; records every request it receives."""

    token: Reply | httpx.HTTPError
    jwks: Reply | httpx.HTTPError
    requests: list[httpx.Request] = field(default_factory=list[httpx.Request])

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        answer = {TOKEN_ENDPOINT: self.token, JWKS_URL: self.jwks}[str(request.url)]
        if isinstance(answer, httpx.HTTPError):
            raise answer
        return answer.response()

    def to(self, url: str) -> list[httpx.Request]:
        return [request for request in self.requests if str(request.url) == url]


@pytest.fixture(scope="module")
def google_key() -> RSAKey:
    return RSAKey.generate_key(2048, parameters={"kid": KID, "alg": "RS256", "use": "sig"})


@pytest.fixture(scope="module")
def impostor_key() -> RSAKey:
    """Another key pair that claims Google's key id."""
    return RSAKey.generate_key(2048, parameters={"kid": KID, "alg": "RS256", "use": "sig"})


@pytest.fixture(scope="module")
def rotated_key() -> RSAKey:
    return RSAKey.generate_key(2048, parameters={"kid": ROTATED_KID, "alg": "RS256", "use": "sig"})


@pytest.fixture
def google(google_key: RSAKey) -> FakeGoogle:
    return FakeGoogle(token=_token_reply(_id_token(google_key)), jwks=_jwks_reply(google_key))


@pytest.fixture
async def http(google: FakeGoogle) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(transport=httpx.MockTransport(google.handle)) as client:
        yield client


@pytest.fixture
def provider(http: httpx.AsyncClient) -> GoogleIdentityProvider:
    return GoogleIdentityProvider(CLIENT_ID, SECRET, http=http)


async def _exchange(provider: IdentityProvider, code: str = CODE) -> IdTokenClaims:
    return await provider.exchange(code, redirect_uri=REDIRECT_URI, code_verifier=VERIFIER)


async def _failure(provider: IdentityProvider) -> AuthError:
    """The `AuthError` that `exchange` raises. Any other exception type escapes `pytest.raises`
    and fails the test. The error says which check failed and nothing else: no secret, no
    token, no email, and no chained exception (a pydantic error would quote its input)."""
    with pytest.raises(AuthError) as excinfo:
        await _exchange(provider)
    error = excinfo.value
    assert type(error) is AuthError
    for text in (str(error), repr(error), *map(str, error.args)):
        assert SECRET_VALUE not in text
        assert EMAIL not in text
        assert ACCESS_TOKEN not in text
    assert error.__cause__ is None
    assert error.__context__ is None
    return error


# --- the fake --------------------------------------------------------------------------------


async def test_fake_returns_the_configured_claims_and_records_the_call() -> None:
    claims = fake_claims(nonce="fake-nonce-0042")
    fake = FakeIdentityProvider(claims)

    assert await _exchange(fake, FAKE_CODE) == claims
    assert fake.calls == [
        ExchangeCall(code=FAKE_CODE, redirect_uri=REDIRECT_URI, code_verifier=VERIFIER)
    ]


async def test_fake_maps_each_code_to_its_claims() -> None:
    first, second = fake_claims(sub="fake-sub-0001"), fake_claims(sub="fake-sub-0002")
    fake = FakeIdentityProvider({"code-a": first, "code-b": second})

    assert await _exchange(fake, "code-b") == second
    assert await _exchange(fake, "code-a") == first
    assert [call.code for call in fake.calls] == ["code-b", "code-a"]


async def test_fake_accepts_a_code_registered_after_it_was_built() -> None:
    fake = FakeIdentityProvider({})
    fake.claims_by_code["code-late"] = fake_claims(nonce="fake-nonce-0099")

    assert (await _exchange(fake, "code-late")).nonce == "fake-nonce-0099"


async def test_fake_refuses_an_unknown_code_and_still_records_the_call() -> None:
    fake = FakeIdentityProvider()

    with pytest.raises(AuthError) as excinfo:
        await _exchange(fake, "code-nobody-issued")

    assert excinfo.value.check == "token_exchange"
    assert fake.calls == [
        ExchangeCall(code="code-nobody-issued", redirect_uri=REDIRECT_URI, code_verifier=VERIFIER)
    ]


def test_fake_defaults_are_synthetic() -> None:
    claims = fake_claims()

    assert (FAKE_SUB, FAKE_EMAIL, FAKE_CLIENT_ID) == (
        "fake-sub-0001",
        "user@example.com",
        "client-id-not-real",
    )
    assert (claims.sub, claims.email, claims.aud) == (FAKE_SUB, FAKE_EMAIL, FAKE_CLIENT_ID)
    assert claims.iss == "https://accounts.google.com"
    assert claims.exp.tzinfo is not None
    assert FakeIdentityProvider().claims_by_code == {FAKE_CODE: claims}


def test_both_providers_satisfy_the_protocol() -> None:
    """Checked by pyright: each assignment fails type-checking if a signature drifts. Building
    the real provider does no I/O."""
    providers: list[IdentityProvider] = [
        FakeIdentityProvider(),
        GoogleIdentityProvider(CLIENT_ID, SECRET),
    ]
    assert len(providers) == 2


@pytest.mark.parametrize("module", [fake_module, provider_module], ids=["fake", "provider"])
def test_module_reads_no_environment_and_no_settings(module: ModuleType) -> None:
    """The fake is chosen by injection only, and the real one is built by its caller."""
    assert ENVIRONMENT_READ.findall(inspect.getsource(module)) == []


# --- the real provider: a valid sign-in ------------------------------------------------------


async def test_a_valid_id_token_comes_back_as_its_claims(provider: GoogleIdentityProvider) -> None:
    claims = await _exchange(provider)

    assert claims.sub == "fake-sub-0001"
    assert claims.email == EMAIL
    assert claims.iss == "https://accounts.google.com"
    assert claims.aud == CLIENT_ID
    assert claims.nonce == NONCE
    assert claims.exp == EXP_AT
    assert claims.exp.utcoffset() is not None
    assert not hasattr(claims, "picture")


async def test_the_token_request_posts_the_code_verifier_and_client_credentials(
    provider: GoogleIdentityProvider, google: FakeGoogle
) -> None:
    await _exchange(provider)

    [request] = google.to(TOKEN_ENDPOINT)
    assert request.method == "POST"
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"
    form = {name: values for name, values in parse_qs(request.content.decode()).items()}
    expected = {
        "grant_type": ["authorization_code"],
        "code": [CODE],
        "redirect_uri": [REDIRECT_URI],
        "code_verifier": [VERIFIER],
        "client_id": [CLIENT_ID],
        "client_secret": [SECRET_VALUE],
    }
    assert form == expected


async def test_the_secret_travels_only_in_the_token_request_body(
    provider: GoogleIdentityProvider, google: FakeGoogle
) -> None:
    await _exchange(provider)

    assert len(google.requests) == 2
    for request in google.requests:
        assert SECRET_VALUE not in str(request.url)
        assert all(SECRET_VALUE not in value for value in request.headers.values())
    [jwks_request] = google.to(JWKS_URL)
    assert SECRET_VALUE not in jwks_request.content.decode()


async def test_the_key_set_is_fetched_with_a_get_after_the_token_request(
    provider: GoogleIdentityProvider, google: FakeGoogle
) -> None:
    await _exchange(provider)

    assert [(request.method, str(request.url)) for request in google.requests] == [
        ("POST", TOKEN_ENDPOINT),
        ("GET", JWKS_URL),
    ]


async def test_both_requests_carry_a_ten_second_timeout(
    provider: GoogleIdentityProvider, google: FakeGoogle
) -> None:
    await _exchange(provider)

    assert HTTP_TIMEOUT == 10.0
    ten_seconds = {"connect": 10.0, "read": 10.0, "write": 10.0, "pool": 10.0}
    assert [request.extensions["timeout"] for request in google.requests] == [ten_seconds] * 2


def test_the_token_response_keeps_only_the_id_token() -> None:
    parsed = TokenResponse.model_validate(
        {"id_token": "a.b.c", "access_token": ACCESS_TOKEN, "token_type": "Bearer"}
    )

    assert set(TokenResponse.model_fields) == {"id_token"}
    assert ACCESS_TOKEN not in repr(parsed)


async def test_the_provider_keeps_no_token_after_an_exchange(
    provider: GoogleIdentityProvider, google: FakeGoogle, google_key: RSAKey
) -> None:
    await _exchange(provider)

    kept = repr(vars(provider))
    assert ACCESS_TOKEN not in kept
    assert _id_token(google_key) not in kept
    assert SECRET_VALUE not in kept
    assert EMAIL not in kept


async def test_an_injected_client_is_left_open(
    provider: GoogleIdentityProvider, http: httpx.AsyncClient
) -> None:
    await _exchange(provider)

    assert not http.is_closed


async def test_without_an_injected_client_the_provider_opens_and_closes_its_own(
    monkeypatch: pytest.MonkeyPatch, google: FakeGoogle
) -> None:
    opened: list[httpx.AsyncClient] = []
    real_client = httpx.AsyncClient

    def client_on_the_fake_google(*, timeout: float) -> httpx.AsyncClient:
        client = real_client(transport=httpx.MockTransport(google.handle), timeout=timeout)
        opened.append(client)
        return client

    monkeypatch.setattr(httpx, "AsyncClient", client_on_the_fake_google)

    claims = await _exchange(GoogleIdentityProvider(CLIENT_ID, SECRET))

    assert claims.sub == "fake-sub-0001"
    assert len(opened) == 1
    assert opened[0].is_closed
    assert opened[0].timeout.read == HTTP_TIMEOUT


async def test_claims_come_back_unchecked_for_validate_claims_to_judge(
    provider: GoogleIdentityProvider, google: FakeGoogle, google_key: RSAKey
) -> None:
    """The provider proves Google signed the token; whether it was issued to us, for this
    attempt, and is still live is `validate_claims`'s call, made by the route with its own
    client id, nonce and clock."""
    foreign = {**CLAIMS, "aud": "another-client-id", "nonce": "another-nonce", "exp": 1}
    google.token = _token_reply(_id_token(google_key, foreign))

    claims = await _exchange(provider)

    assert (claims.aud, claims.nonce) == ("another-client-id", "another-nonce")
    assert claims.exp == datetime.fromtimestamp(1, UTC)


# --- the key cache ---------------------------------------------------------------------------


async def test_a_cached_key_is_not_fetched_again(
    provider: GoogleIdentityProvider, google: FakeGoogle
) -> None:
    await _exchange(provider)
    await _exchange(provider)

    assert len(google.to(TOKEN_ENDPOINT)) == 2
    assert len(google.to(JWKS_URL)) == 1


async def test_an_unknown_kid_is_refetched_once_then_rejected(
    provider: GoogleIdentityProvider, google: FakeGoogle, google_key: RSAKey
) -> None:
    await _exchange(provider)
    google.token = _token_reply(_id_token(google_key, kid=ROTATED_KID))

    assert (await _failure(provider)).check == "id_token"
    assert len(google.to(JWKS_URL)) == 2


async def test_a_fresh_provider_fetches_once_for_an_unknown_kid(
    provider: GoogleIdentityProvider, google: FakeGoogle, google_key: RSAKey
) -> None:
    google.token = _token_reply(_id_token(google_key, kid=ROTATED_KID))

    assert (await _failure(provider)).check == "id_token"
    assert len(google.to(JWKS_URL)) == 1


async def test_a_rotated_key_is_picked_up_by_one_refetch(
    provider: GoogleIdentityProvider,
    google: FakeGoogle,
    google_key: RSAKey,
    rotated_key: RSAKey,
) -> None:
    await _exchange(provider)
    google.jwks = _jwks_reply(google_key, rotated_key)
    google.token = _token_reply(_id_token(rotated_key, kid=ROTATED_KID))

    assert (await _exchange(provider)).sub == "fake-sub-0001"
    assert len(google.to(JWKS_URL)) == 2


# --- the real provider: refusals -------------------------------------------------------------

TokenMaker = Callable[[RSAKey, RSAKey], str]

REJECTED_ID_TOKENS: dict[str, TokenMaker] = {
    "signed-by-another-key": lambda google, impostor: _id_token(impostor),
    "hs256-shared-secret": lambda google, impostor: jwt.encode(
        {"alg": "HS256", "kid": KID},
        CLAIMS,
        OctKey.import_key("synthetic-shared-secret-not-real-0001"),
        algorithms=["HS256"],
    ),
    "rs512-google-key": lambda google, impostor: _id_token(_without_alg(google), alg="RS512"),
    "alg-none": lambda google, impostor: (
        _encode({"alg": "none", "kid": KID}) + "." + _encode(CLAIMS) + "."
    ),
    "payload-tampered": lambda google, impostor: _tampered(_id_token(google)),
    "no-kid": lambda google, impostor: jwt.encode(
        {"alg": "RS256"}, CLAIMS, google, algorithms=["RS256"]
    ),
    "kid-not-a-string": lambda google, impostor: _unsigned({"alg": "RS256", "kid": 5}),
    # joserfc 1.8.0 raises a bare TypeError for each of the next five before any signature
    # check: `jwt.decode` for the two `crit` shapes and a list header, and `jws.extract_compact`
    # already for a list or a string header that contains "b64" (it indexes `header["b64"]`).
    "crit-not-a-list": lambda google, impostor: _unsigned(
        {"alg": "RS256", "kid": KID, "crit": True}
    ),
    "crit-list-of-numbers": lambda google, impostor: _unsigned(
        {"alg": "RS256", "kid": KID, "crit": [1]}
    ),
    "header-is-a-list": lambda google, impostor: _unsigned(["alg", "RS256"]),
    "header-list-naming-b64": lambda google, impostor: _unsigned(["alg", "b64"]),
    "header-text-naming-alg-and-b64": lambda google, impostor: _unsigned("alg b64"),
    "header-not-json": lambda google, impostor: "bm90LWpzb24." + _encode(CLAIMS) + ".AAAA",
    "one-word": lambda google, impostor: "garbage",
    "three-words": lambda google, impostor: "a.b.c",
    "non-ascii": lambda google, impostor: "é.é.é",
    "payload-is-a-list": lambda google, impostor: jws.serialize_compact(
        {"alg": "RS256", "kid": KID}, b"[1, 2]", google, algorithms=["RS256"]
    ),
    "missing-nonce": lambda google, impostor: _id_token(google, _without("nonce")),
    "missing-email": lambda google, impostor: _id_token(google, _without("email")),
    "audience-is-a-list": lambda google, impostor: _id_token(
        google, {**CLAIMS, "aud": [CLIENT_ID]}
    ),
}


@pytest.mark.parametrize("case", list(REJECTED_ID_TOKENS))
async def test_an_id_token_that_fails_verification_is_refused(
    case: str,
    provider: GoogleIdentityProvider,
    google: FakeGoogle,
    google_key: RSAKey,
    impostor_key: RSAKey,
) -> None:
    google.token = _token_reply(REJECTED_ID_TOKENS[case](google_key, impostor_key))

    assert (await _failure(provider)).check == "id_token"


async def test_only_rs256_is_accepted_even_from_a_key_set_without_alg(
    provider: GoogleIdentityProvider, google: FakeGoogle, google_key: RSAKey
) -> None:
    """Google's keys carry `alg: RS256`, and joserfc then refuses another algorithm by itself.
    Without that parameter only the provider's pin stands between an RS512 token and its key."""
    bare = _without_alg(google_key)
    google.jwks = _jwks_reply(bare)
    google.token = _token_reply(_id_token(bare, alg="RS512"))

    assert (await _failure(provider)).check == "id_token"

    google.token = _token_reply(_id_token(bare))
    assert (await _exchange(provider)).sub == "fake-sub-0001"


async def test_a_symmetric_key_in_the_key_set_cannot_verify_an_hs256_token(
    provider: GoogleIdentityProvider, google: FakeGoogle, google_key: RSAKey
) -> None:
    """Two guards stand here: the RS256 pin, and a key set reduced to RSA keys. Either one
    alone refuses this token."""
    shared = "synthetic-shared-secret-not-real-0002"
    raw = base64.urlsafe_b64encode(shared.encode()).rstrip(b"=").decode()
    symmetric = {"kty": "oct", "kid": ROTATED_KID, "k": raw}
    google.jwks = _json({"keys": [google_key.as_dict(private=False), symmetric]})
    google.token = _token_reply(
        jwt.encode(
            {"alg": "HS256", "kid": ROTATED_KID},
            CLAIMS,
            OctKey.import_key(shared),
            algorithms=["HS256"],
        )
    )

    assert (await _failure(provider)).check == "id_token"


async def test_a_non_2xx_token_reply_is_refused_even_with_an_id_token(
    provider: GoogleIdentityProvider, google: FakeGoogle, google_key: RSAKey
) -> None:
    usable = _token_reply(_id_token(google_key))
    google.token = Reply(500, usable.body)

    assert (await _failure(provider)).check == "token_exchange"
    assert google.to(JWKS_URL) == []


async def test_a_non_2xx_key_set_reply_is_refused_even_with_usable_keys(
    provider: GoogleIdentityProvider, google: FakeGoogle, google_key: RSAKey
) -> None:
    google.jwks = Reply(404, _jwks_reply(google_key).body)

    assert (await _failure(provider)).check == "jwks"


REFUSED_TOKEN_RESPONSES: dict[str, Reply | httpx.HTTPError] = {
    "status-400": _json({"error": "invalid_grant"}, status=400),
    "status-401": _json({"error": "invalid_client"}, status=401),
    "status-500": _json({"error": "internal"}, status=500),
    "status-302": Reply(302, b""),
    "not-json": Reply(200, b"<html>not json</html>"),
    "json-list": _json([]),
    "no-id-token": _json({"access_token": ACCESS_TOKEN, "token_type": "Bearer"}),
    "empty-id-token": _json({"id_token": "", "access_token": ACCESS_TOKEN}),
    "id-token-not-a-string": _json({"id_token": 123, "access_token": ACCESS_TOKEN}),
    "connect-error": httpx.ConnectError("synthetic connect failure"),
    "read-timeout": httpx.ReadTimeout("synthetic timeout"),
}


@pytest.mark.parametrize("case", list(REFUSED_TOKEN_RESPONSES))
async def test_a_failed_token_exchange_is_refused_before_any_key_fetch(
    case: str, provider: GoogleIdentityProvider, google: FakeGoogle
) -> None:
    google.token = REFUSED_TOKEN_RESPONSES[case]

    assert (await _failure(provider)).check == "token_exchange"
    assert google.to(JWKS_URL) == []


def _symmetric_key_set() -> Reply:
    return _json({"keys": [{"kty": "oct", "kid": KID, "k": "c3ludGhldGljLW5vdC1yZWFs"}]})


REFUSED_KEY_SETS: dict[str, Callable[[RSAKey], Reply | httpx.HTTPError]] = {
    "status-500": lambda key: _json({"error": "internal"}, status=500),
    "not-json": lambda key: Reply(200, b"<html>not json</html>"),
    "no-keys-field": lambda key: _json({}),
    "empty-keys": lambda key: _json({"keys": []}),
    "unknown-key-type-only": lambda key: _json({"keys": [{"kty": "XX", "kid": KID}]}),
    "bad-modulus": lambda key: _json(
        {"keys": [{"kty": "RSA", "kid": KID, "n": "!!", "e": "AQAB"}]}
    ),
    "missing-exponent": lambda key: _json(
        {"keys": [{"kty": "RSA", "kid": KID, "n": key.as_dict(private=False)["n"]}]}
    ),
    "exponent-not-a-string": lambda key: _json(
        {"keys": [{"kty": "RSA", "kid": KID, "n": key.as_dict(private=False)["n"], "e": 65537}]}
    ),
    "symmetric-key-only": lambda key: _symmetric_key_set(),
    "connect-timeout": lambda key: httpx.ConnectTimeout("synthetic timeout"),
}


@pytest.mark.parametrize("case", list(REFUSED_KEY_SETS))
async def test_a_key_set_that_cannot_be_used_is_refused(
    case: str, provider: GoogleIdentityProvider, google: FakeGoogle, google_key: RSAKey
) -> None:
    google.jwks = REFUSED_KEY_SETS[case](google_key)

    assert (await _failure(provider)).check == "jwks"
    assert len(google.to(JWKS_URL)) == 1
