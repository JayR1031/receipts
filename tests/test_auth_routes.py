"""Issue #41 `routes`: `/auth/login`, `/auth/callback`, `/auth/logout`, `/auth/me` (ADR-0008).

The app is built here: `FastAPI()` plus the auth router, with a `FakeIdentityProvider`, a
`SqlUserRepo` on SQLite `:memory:` and a fixed, timezone-aware clock on `app.state`. Settings
come from synthetic environment values set with `monkeypatch`, never from the shell. No network:
the fake answers every token exchange, and the one real provider built here is never called.

Cookies. Both auth cookies are `Secure`. An `http://` client's cookie jar never sends a `Secure`
cookie back, while a browser treats `http://localhost` as a secure context and does, so
`Browser` below plays the browser: it keeps what each response sets, drops what a response
clears (`Max-Age=0`) and sends the rest in a `Cookie` header.

Synthetic identities only: `fake-sub-0001`, `user@example.com`, `client-id-not-real`.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from http.cookies import Morsel, SimpleCookie
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qsl, urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.orm import Session
from starlette.requests import Request

from receipts.auth import routes
from receipts.auth.fake import (
    FAKE_CLIENT_ID,
    FAKE_EMAIL,
    FAKE_SUB,
    ExchangeCall,
    FakeIdentityProvider,
    fake_claims,
)
from receipts.auth.models import IdTokenClaims, SessionUser, User
from receipts.auth.oidc import (
    GOOGLE_AUTHORIZATION_ENDPOINT,
    LOCAL_CALLBACK_URL,
    OAuthRoundTrip,
    code_challenge,
)
from receipts.auth.provider import GoogleIdentityProvider
from receipts.auth.session import (
    ROUND_TRIP_COOKIE,
    ROUND_TRIP_MAX_AGE,
    ROUND_TRIP_TTL,
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    SESSION_TTL,
    new_session,
    sign_round_trip,
    sign_session,
    verify_round_trip,
    verify_session,
)
from receipts.db import SqlUserRepo, UserRow, create_schema, make_engine
from receipts.settings import Settings, get_settings

# Far from the real date on purpose: a route that read the wall clock instead of `app.state.clock`
# would sign and check cookies and claims at a time these tests never use, and go red.
NOW = datetime(2030, 3, 4, 12, 0, tzinfo=UTC)
CLIENT_ID = FAKE_CLIENT_ID
CLIENT_SECRET = "client-secret-not-real-5c1d"
SESSION_SECRET = "session-secret-not-real-9e2b7a41"
# Synthetic and never opened: the injected repo answers. Sign-in needs the name to be set.
DATABASE_URL = "sqlite+pysqlite:///:memory:"
SIGN_IN_ENV = {
    "GOOGLE_CLIENT_ID": CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": CLIENT_SECRET,
    "SESSION_SECRET": SESSION_SECRET,
    "DATABASE_URL": DATABASE_URL,
}
SIGN_IN_NAMES = tuple(SIGN_IN_ENV)
CODE = "code-1"
LOCAL_BASE = "http://localhost:8000"


# --- harness -----------------------------------------------------------------------------


class Headers(Protocol):
    def __getitem__(self, key: str) -> str: ...
    def __contains__(self, key: object) -> bool: ...
    def get_list(self, key: str, split_commas: bool = False) -> list[str]: ...


class Reply(Protocol):
    """What these tests read from a `TestClient` response (httpx's or httpx2's)."""

    @property
    def status_code(self) -> int: ...
    @property
    def text(self) -> str: ...
    @property
    def headers(self) -> Headers: ...
    def json(self) -> object: ...


@dataclass
class Clock:
    now: datetime = NOW

    def __call__(self) -> datetime:
        return self.now


def set_cookies(response: Reply) -> dict[str, Morsel[str]]:
    """Every `Set-Cookie` header of `response`, parsed, by cookie name."""
    parsed: dict[str, Morsel[str]] = {}
    for header in response.headers.get_list("set-cookie"):
        jar: SimpleCookie = SimpleCookie()
        jar.load(header)
        parsed.update(jar)
    return parsed


def cleared(morsel: Morsel[str]) -> bool:
    return morsel["max-age"] == "0"


@dataclass
class Browser:
    """A `TestClient` that keeps cookies the way a browser on `http://localhost` does."""

    client: TestClient
    cookies: dict[str, str] = field(default_factory=dict[str, str])

    def get(self, url: str, params: dict[str, str] | None = None) -> Reply:
        return self._send("GET", url, params)

    def post(self, url: str) -> Reply:
        return self._send("POST", url, None)

    def _send(self, method: str, url: str, params: dict[str, str] | None) -> Reply:
        headers = {"Cookie": "; ".join(f"{k}={v}" for k, v in self.cookies.items())}
        response = self.client.request(
            method, url, params=params, headers=headers if self.cookies else None
        )
        self.client.cookies.clear()  # only `self.cookies` is ever sent
        for name, morsel in set_cookies(response).items():
            if cleared(morsel):
                self.cookies.pop(name, None)
            else:
                self.cookies[name] = morsel.value
        return response


@dataclass
class Harness:
    app: FastAPI
    browser: Browser
    fake: FakeIdentityProvider
    engine: Engine
    clock: Clock


@pytest.fixture
def sign_in_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name, value in SIGN_IN_ENV.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(routes.router)
    return app


def _client(app: FastAPI, base_url: str = LOCAL_BASE) -> TestClient:
    return TestClient(app, base_url=base_url, follow_redirects=False)


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = make_engine("sqlite:///:memory:")
    asyncio.run(create_schema(engine))
    yield engine
    engine.dispose()


@pytest.fixture
def h(sign_in_env: None, engine: Engine) -> Harness:
    app = _app()
    fake = FakeIdentityProvider({})
    clock = Clock()
    app.state.identity_provider = fake
    app.state.user_repo = SqlUserRepo(engine=engine)
    app.state.clock = clock
    return Harness(app=app, browser=Browser(_client(app)), fake=fake, engine=engine, clock=clock)


def user_rows(engine: Engine) -> list[tuple[str, str, str]]:
    with Session(engine) as session:
        rows = session.scalars(select(UserRow)).all()
        return [(row.id, row.sub, row.email) for row in rows]


def user_count(engine: Engine) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(UserRow)) or 0


def payload(token: str) -> dict[str, object]:
    """A JWT's claims, decoded without checking the signature: what the browser can read."""
    segment = token.split(".")[1]
    decoded: dict[str, object] = json.loads(
        base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    )
    return decoded


def login(h: Harness, *, now: datetime = NOW) -> OAuthRoundTrip:
    """`GET /auth/login`, then read the attempt back from the round-trip cookie it set."""
    response = h.browser.get("/auth/login")
    assert response.status_code == 302, response.text
    attempt = verify_round_trip(
        h.browser.cookies[ROUND_TRIP_COOKIE], secret=SecretStr(SESSION_SECRET), now=now
    )
    assert attempt is not None
    return attempt


def callback(h: Harness, attempt: OAuthRoundTrip, claims: IdTokenClaims) -> Reply:
    """Register `claims` for `CODE`, then come back from Google with this attempt's state."""
    h.fake.claims_by_code[CODE] = claims
    return h.browser.get("/auth/callback", params={"code": CODE, "state": attempt.state})


def sign_in(h: Harness) -> Reply:
    attempt = login(h)
    return callback(h, attempt, fake_claims(nonce=attempt.nonce, aud=CLIENT_ID))


def session_of(h: Harness) -> SessionUser | None:
    token = h.browser.cookies.get(SESSION_COOKIE)
    if token is None:
        return None
    return verify_session(token, secret=SecretStr(SESSION_SECRET), now=h.clock.now)


def assert_auth_flags(morsel: Morsel[str]) -> None:
    assert morsel["httponly"] is True
    assert morsel["secure"] is True
    assert morsel["samesite"] == "lax"
    assert morsel["path"] == "/"


# --- GET /auth/login ---------------------------------------------------------------------


def test_login_redirects_to_google_with_state_nonce_pkce_and_the_local_callback(
    h: Harness,
) -> None:
    response = h.browser.get("/auth/login")
    assert response.status_code == 302
    location = urlsplit(response.headers["location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == GOOGLE_AUTHORIZATION_ENDPOINT
    pairs = parse_qsl(location.query, strict_parsing=True)
    query = dict(pairs)
    assert len(query) == len(pairs), "a parameter is repeated"
    attempt = verify_round_trip(
        h.browser.cookies[ROUND_TRIP_COOKIE], secret=SecretStr(SESSION_SECRET), now=NOW
    )
    assert attempt is not None
    assert query == {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": "http://localhost:8000/auth/callback",
        "scope": "openid email",
        "state": attempt.state,
        "nonce": attempt.nonce,
        "code_challenge": code_challenge(attempt.code_verifier),
        "code_challenge_method": "S256",
    }


def test_login_sets_only_the_round_trip_cookie_with_the_flags_and_ten_minutes(h: Harness) -> None:
    response = h.browser.get("/auth/login")
    cookies = set_cookies(response)
    assert set(cookies) == {ROUND_TRIP_COOKIE}
    morsel = cookies[ROUND_TRIP_COOKIE]
    assert_auth_flags(morsel)
    assert morsel["max-age"] == str(ROUND_TRIP_MAX_AGE)


def test_the_round_trip_cookie_is_signed_at_the_clock_and_lasts_ten_minutes(h: Harness) -> None:
    h.browser.get("/auth/login")
    token = h.browser.cookies[ROUND_TRIP_COOKIE]
    secret = SecretStr(SESSION_SECRET)
    assert verify_round_trip(token, secret=secret, now=NOW + ROUND_TRIP_TTL - timedelta(seconds=1))
    assert verify_round_trip(token, secret=secret, now=NOW + ROUND_TRIP_TTL) is None


def test_each_login_is_a_fresh_attempt(h: Harness) -> None:
    first, second = login(h), login(h)
    assert first.state != second.state
    assert first.nonce != second.nonce
    assert first.code_verifier != second.code_verifier


@pytest.mark.parametrize("base_url", ["http://127.0.0.1:8000", "http://127.0.0.1:7860"])
def test_login_on_127_0_0_1_goes_to_localhost_first_and_sets_no_cookie(
    h: Harness, base_url: str
) -> None:
    response = _client(h.app, base_url).get("/auth/login")
    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:8000/auth/login"
    assert "set-cookie" not in response.headers


def test_login_on_the_deployed_host_uses_its_https_callback(h: Harness) -> None:
    response = _client(h.app, "https://receipts-h745.onrender.com").get("/auth/login")
    query = dict(parse_qsl(urlsplit(response.headers["location"]).query))
    assert query["redirect_uri"] == "https://receipts-h745.onrender.com/auth/callback"


# --- GET /auth/callback ------------------------------------------------------------------


def test_a_valid_callback_creates_one_user_and_sets_the_session_cookie(h: Harness) -> None:
    attempt = login(h)
    response = callback(h, attempt, fake_claims(nonce=attempt.nonce, aud=CLIENT_ID))
    assert response.status_code == 302, response.text
    assert response.headers["location"] == "/ui"
    rows = user_rows(h.engine)
    assert len(rows) == 1, f"{len(rows)} of 1 users rows"
    user_id, sub, email = rows[0]
    assert (sub, email) == (FAKE_SUB, FAKE_EMAIL)
    assert session_of(h) == SessionUser(user_id=user_id, expires_at=NOW + SESSION_TTL)
    assert h.fake.calls == [
        ExchangeCall(
            code=CODE, redirect_uri=LOCAL_CALLBACK_URL, code_verifier=attempt.code_verifier
        )
    ]


def test_the_session_cookie_has_the_flags_and_seven_days(h: Harness) -> None:
    response = sign_in(h)
    cookies = set_cookies(response)
    session = cookies[SESSION_COOKIE]
    assert_auth_flags(session)
    assert session["max-age"] == str(SESSION_MAX_AGE)
    assert cleared(cookies[ROUND_TRIP_COOKIE])
    assert_auth_flags(cookies[ROUND_TRIP_COOKIE])
    raw = response.headers.get_list("set-cookie")
    line = next(value for value in raw if value.startswith(f"{SESSION_COOKIE}="))
    assert all(flag in line for flag in ("HttpOnly", "Secure", "SameSite=lax", "Path=/"))


def test_the_session_cookie_carries_the_user_id_and_expiry_only(h: Harness) -> None:
    sign_in(h)
    claims = payload(h.browser.cookies[SESSION_COOKIE])
    ((user_id, _sub, _email),) = user_rows(h.engine)
    assert set(claims) == {"uid", "exp"}
    assert claims["uid"] == user_id
    assert FAKE_EMAIL not in json.dumps(claims)
    assert FAKE_SUB not in json.dumps(claims)


def test_a_second_sign_in_with_the_same_sub_reuses_the_row(h: Harness) -> None:
    sign_in(h)
    first = session_of(h)
    sign_in(h)
    second = session_of(h)
    assert user_count(h.engine) == 1, f"{user_count(h.engine)} of 1 users rows"
    assert first is not None and second is not None
    assert first.user_id == second.user_id == user_rows(h.engine)[0][0]


@pytest.mark.parametrize(
    "state",
    [pytest.param("wrong-state", id="wrong"), pytest.param("", id="empty"), None],
)
def test_a_callback_with_a_wrong_state_is_400_and_sets_no_session(
    h: Harness, state: str | None
) -> None:
    attempt = login(h)
    h.fake.claims_by_code[CODE] = fake_claims(nonce=attempt.nonce, aud=CLIENT_ID)
    params = {"code": CODE} if state is None else {"code": CODE, "state": state}
    response = h.browser.get("/auth/callback", params=params)
    assert response.status_code == 400
    assert response.json() == {"detail": "sign-in check failed: state"}
    cookies = set_cookies(response)
    assert SESSION_COOKIE not in cookies
    assert cleared(cookies[ROUND_TRIP_COOKIE])
    assert_auth_flags(cookies[ROUND_TRIP_COOKIE])  # same path and flags, or the browser keeps it
    assert h.fake.calls == []
    assert user_count(h.engine) == 0


def test_a_callback_with_a_state_that_only_shares_a_prefix_is_400(h: Harness) -> None:
    attempt = login(h)
    h.fake.claims_by_code[CODE] = fake_claims(nonce=attempt.nonce, aud=CLIENT_ID)
    for state in (attempt.state[:-1], attempt.state + "x", attempt.state.upper()):
        h.browser.cookies[ROUND_TRIP_COOKIE] = sign_round_trip(
            attempt, secret=SecretStr(SESSION_SECRET), now=NOW
        )
        response = h.browser.get("/auth/callback", params={"code": CODE, "state": state})
        assert response.status_code == 400
        assert SESSION_COOKIE not in set_cookies(response)
    assert user_count(h.engine) == 0


def test_a_callback_without_a_code_is_400(h: Harness) -> None:
    attempt = login(h)
    response = h.browser.get("/auth/callback", params={"state": attempt.state})
    assert response.status_code == 400
    assert response.json() == {"detail": "sign-in check failed: code"}
    assert SESSION_COOKIE not in set_cookies(response)
    assert h.fake.calls == []


def _tampered(token: str) -> str:
    index = len(token) // 2
    return token[:index] + ("A" if token[index] != "A" else "B") + token[index + 1 :]


@pytest.mark.parametrize("case", ["missing", "tampered", "other-secret", "expired"])
def test_a_callback_without_a_valid_round_trip_cookie_is_400_and_sets_no_cookie(
    h: Harness, case: str
) -> None:
    attempt = login(h)
    h.fake.claims_by_code[CODE] = fake_claims(nonce=attempt.nonce, aud=CLIENT_ID)
    if case == "missing":
        del h.browser.cookies[ROUND_TRIP_COOKIE]
    elif case == "tampered":
        h.browser.cookies[ROUND_TRIP_COOKIE] = _tampered(h.browser.cookies[ROUND_TRIP_COOKIE])
    elif case == "other-secret":
        other = SecretStr("another-session-secret-not-real")
        h.browser.cookies[ROUND_TRIP_COOKIE] = sign_round_trip(attempt, secret=other, now=NOW)
    else:
        h.clock.now = NOW + ROUND_TRIP_TTL
    response = h.browser.get("/auth/callback", params={"code": CODE, "state": attempt.state})
    assert response.status_code == 400
    assert response.json() == {"detail": "sign-in check failed: round_trip"}
    assert "set-cookie" not in response.headers
    assert h.fake.calls == []
    assert user_count(h.engine) == 0


def _wrong_nonce(attempt: OAuthRoundTrip) -> IdTokenClaims:
    return fake_claims(nonce="another-nonce-0002", aud=CLIENT_ID)


def _wrong_aud(attempt: OAuthRoundTrip) -> IdTokenClaims:
    return fake_claims(nonce=attempt.nonce, aud="another-client-id-not-real")


def _wrong_iss(attempt: OAuthRoundTrip) -> IdTokenClaims:
    return fake_claims(nonce=attempt.nonce, aud=CLIENT_ID, iss="https://issuer.example.com")


def _expiring(attempt: OAuthRoundTrip) -> IdTokenClaims:
    return fake_claims(nonce=attempt.nonce, aud=CLIENT_ID, exp=NOW + timedelta(minutes=5))


@pytest.mark.parametrize(
    ("make", "check", "advance"),
    [
        pytest.param(_wrong_nonce, "nonce", timedelta(0), id="wrong-nonce"),
        pytest.param(_wrong_aud, "aud", timedelta(0), id="wrong-aud"),
        pytest.param(_wrong_iss, "iss", timedelta(0), id="wrong-iss"),
        # Live at login, expired by the callback: the clock is read when Google sends us back.
        pytest.param(_expiring, "exp", timedelta(minutes=6), id="expired-exp"),
    ],
)
def test_claims_that_fail_validation_set_no_session_and_write_no_row(
    h: Harness, make: Callable[[OAuthRoundTrip], IdTokenClaims], check: str, advance: timedelta
) -> None:
    attempt = login(h)
    claims = make(attempt)
    h.clock.now = NOW + advance
    response = callback(h, attempt, claims)
    assert response.status_code == 400
    assert response.json() == {"detail": f"sign-in check failed: {check}"}
    cookies = set_cookies(response)
    assert SESSION_COOKIE not in cookies
    assert cleared(cookies[ROUND_TRIP_COOKIE])
    assert_auth_flags(cookies[ROUND_TRIP_COOKIE])  # same path and flags, or the browser keeps it
    assert user_count(h.engine) == 0
    assert len(h.fake.calls) == 1


def test_claims_live_at_the_callback_clock_are_accepted(h: Harness) -> None:
    attempt = login(h)
    h.clock.now = NOW + timedelta(minutes=4)
    response = callback(h, attempt, _expiring(attempt))
    assert response.status_code == 302
    assert user_count(h.engine) == 1


def test_a_provider_refusal_is_400_naming_its_check_only(h: Harness) -> None:
    attempt = login(h)
    response = h.browser.get(
        "/auth/callback", params={"code": "code-google-refused", "state": attempt.state}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "sign-in check failed: token_exchange"}
    assert SESSION_COOKIE not in set_cookies(response)
    assert "code-google-refused" not in response.text
    assert user_count(h.engine) == 0


def test_a_refusal_never_echoes_the_email_the_code_or_a_cookie(h: Harness) -> None:
    attempt = login(h)
    round_trip = h.browser.cookies[ROUND_TRIP_COOKIE]
    response = callback(h, attempt, _wrong_nonce(attempt))
    for value in (FAKE_EMAIL, FAKE_SUB, CODE, attempt.state, attempt.nonce, round_trip):
        assert value not in response.text


# A second synthetic identity, so the leak checks below cannot match a value set elsewhere.
STORE_SUB = "fake-sub-store-0002"
STORE_EMAIL = "store-user@example.com"


@dataclass
class FailingUserRepo:
    """A `users` store that is down. `get_or_create` raises as `SqlUserRepo` would: an error
    whose text carries the statement's bound parameters, so the `sub` and email it was given."""

    error: type[DBAPIError]
    raised: list[DBAPIError] = field(default_factory=list[DBAPIError])

    async def get_or_create(self, sub: str, email: str, now: datetime) -> User:
        error = self.error(
            "INSERT INTO users (id, sub, email, created_at) VALUES (?, ?, ?, ?)",
            ("user-store-0002", sub, email, now.isoformat()),
            Exception("database is locked"),
        )
        self.raised.append(error)
        raise error


def _logged(records: list[logging.LogRecord]) -> str:
    """Every record as a handler would write it, traceback and exception text included."""
    formatter = logging.Formatter("%(name)s %(levelname)s %(message)s")
    return "\n".join(formatter.format(record) for record in records)


@pytest.mark.parametrize("error", [OperationalError, IntegrityError])
def test_a_user_store_failure_is_503_clears_the_round_trip_and_leaks_no_identity(
    h: Harness,
    error: type[DBAPIError],
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verdict `routes` finding 1. The default `TestClient` re-raises an exception that escapes
    the app, which is what uvicorn would log with its text: the email and the `sub`."""
    caplog.set_level(logging.DEBUG)
    repo = FailingUserRepo(error)
    h.app.state.user_repo = repo
    attempt = login(h)
    claims = fake_claims(sub=STORE_SUB, email=STORE_EMAIL, nonce=attempt.nonce, aud=CLIENT_ID)
    response = callback(h, attempt, claims)
    assert response.status_code == 503, response.text
    assert response.json() == {"detail": "sign-in check failed: user_store"}
    cookies = set_cookies(response)
    assert SESSION_COOKIE not in cookies
    assert cleared(cookies[ROUND_TRIP_COOKIE])
    assert_auth_flags(cookies[ROUND_TRIP_COOKIE])
    assert ROUND_TRIP_COOKIE not in h.browser.cookies
    (raised,) = repo.raised
    assert STORE_EMAIL in str(raised) and STORE_SUB in str(raised), "the error carries both"
    captured = capsys.readouterr()
    places = {
        "response": "\n".join([response.text, *response.headers.get_list("set-cookie")]),
        "log": _logged(caplog.records),
        "stdout or stderr": captured.out + captured.err,
    }
    for place, text in places.items():
        for value in (STORE_EMAIL, STORE_SUB):
            assert value not in text, f"{value} reached the {place}"


# --- POST /auth/logout -------------------------------------------------------------------


def test_logout_clears_the_session_cookie_and_goes_to_the_ui(h: Harness) -> None:
    sign_in(h)
    assert SESSION_COOKIE in h.browser.cookies
    response = h.browser.post("/auth/logout")
    assert response.status_code == 303
    assert response.headers["location"] == "/ui"
    morsel = set_cookies(response)[SESSION_COOKIE]
    assert cleared(morsel)
    assert_auth_flags(morsel)  # same path and flags, or the browser keeps the cookie
    assert SESSION_COOKIE not in h.browser.cookies


def test_logout_works_when_sign_in_is_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in SIGN_IN_NAMES:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    response = _client(_app()).post("/auth/logout")
    assert response.status_code == 303
    assert cleared(set_cookies(response)[SESSION_COOKIE])


# --- GET /auth/me ------------------------------------------------------------------------


def test_me_is_401_signed_out(h: Harness) -> None:
    assert h.browser.get("/auth/me").status_code == 401


def test_me_returns_the_email_signed_in_and_is_not_cached(h: Harness) -> None:
    sign_in(h)
    response = h.browser.get("/auth/me")
    assert response.status_code == 200
    assert response.json() == {"email": "user@example.com"}
    assert response.headers["cache-control"] == "no-store"


def test_me_is_401_with_a_tampered_cookie(h: Harness) -> None:
    sign_in(h)
    h.browser.cookies[SESSION_COOKIE] = _tampered(h.browser.cookies[SESSION_COOKIE])
    assert h.browser.get("/auth/me").status_code == 401


def test_me_is_401_after_logout(h: Harness) -> None:
    sign_in(h)
    assert h.browser.get("/auth/me").status_code == 200
    h.browser.post("/auth/logout")
    assert h.browser.get("/auth/me").status_code == 401


def test_me_is_401_once_the_session_expires(h: Harness) -> None:
    sign_in(h)
    h.clock.now = NOW + SESSION_TTL - timedelta(seconds=1)
    assert h.browser.get("/auth/me").status_code == 200
    h.clock.now = NOW + SESSION_TTL
    assert h.browser.get("/auth/me").status_code == 401


def test_me_is_401_for_a_session_signed_with_another_secret(h: Harness) -> None:
    sign_in(h)
    ((user_id, _sub, _email),) = user_rows(h.engine)
    other = SecretStr("another-session-secret-not-real")
    h.browser.cookies[SESSION_COOKIE] = sign_session(new_session(user_id, now=NOW), secret=other)
    assert h.browser.get("/auth/me").status_code == 401


def test_me_is_401_for_a_session_whose_user_does_not_exist(h: Harness) -> None:
    session = new_session("user-deleted-0001", now=NOW)
    h.browser.cookies[SESSION_COOKIE] = sign_session(session, secret=SecretStr(SESSION_SECRET))
    assert h.browser.get("/auth/me").status_code == 401


def test_me_is_401_when_sign_in_is_not_configured(
    h: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    sign_in(h)
    monkeypatch.delenv("GOOGLE_CLIENT_ID")
    get_settings.cache_clear()
    assert h.browser.get("/auth/me").status_code == 401


# --- current_user (for wiring's Gate.identify) ---------------------------------------------


def _request(app: FastAPI, cookie: str | None = None) -> Request:
    headers = [] if cookie is None else [(b"cookie", f"{SESSION_COOKIE}={cookie}".encode())]
    return Request({"type": "http", "app": app, "headers": headers})


def test_current_user_reads_the_session_cookie_only(h: Harness) -> None:
    session = new_session("user-0001", now=NOW)
    token = sign_session(session, secret=SecretStr(SESSION_SECRET))
    settings = get_settings()
    assert routes.current_user(_request(h.app, token), settings, h.clock) == session
    assert routes.current_user(_request(h.app), settings, h.clock) is None
    assert routes.current_user(_request(h.app, _tampered(token)), settings, h.clock) is None
    expired = Clock(NOW + SESSION_TTL)
    assert routes.current_user(_request(h.app, token), settings, expired) is None


@pytest.mark.parametrize("name", SIGN_IN_NAMES)
def test_current_user_is_none_while_sign_in_is_not_configured(h: Harness, name: str) -> None:
    token = sign_session(new_session("user-0001", now=NOW), secret=SecretStr(SESSION_SECRET))
    settings = Settings.model_validate({**_lower(SIGN_IN_ENV), name.lower(): None})
    assert routes.current_user(_request(h.app, token), settings, h.clock) is None


def _lower(env: dict[str, str]) -> dict[str, str]:
    return {name.lower(): value for name, value in env.items()}


# --- availability: 503 naming the missing variable ----------------------------------------


@pytest.mark.parametrize("path", ["/auth/login", "/auth/callback?code=c&state=s"])
@pytest.mark.parametrize("blank", [False, True], ids=["unset", "blank"])
@pytest.mark.parametrize("name", SIGN_IN_NAMES)
def test_sign_in_is_503_naming_each_missing_variable_and_no_value(
    h: Harness, monkeypatch: pytest.MonkeyPatch, name: str, blank: bool, path: str
) -> None:
    if blank:
        monkeypatch.setenv(name, "   ")
    else:
        monkeypatch.delenv(name)
    get_settings.cache_clear()
    response = h.browser.get(path)
    assert response.status_code == 503
    assert response.json() == {"detail": f"{name} is not set"}
    for value in SIGN_IN_ENV.values():
        assert value not in response.text
    assert "set-cookie" not in response.headers
    assert h.fake.calls == []


def test_the_503_names_the_first_missing_variable_in_order(
    h: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SESSION_SECRET")
    monkeypatch.delenv("DATABASE_URL")
    get_settings.cache_clear()
    assert h.browser.get("/auth/login").json() == {"detail": "SESSION_SECRET is not set"}


def test_missing_sign_in_settings_names_the_four_in_order() -> None:
    assert routes.missing_sign_in_settings(Settings.model_validate({})) == SIGN_IN_NAMES
    assert routes.missing_sign_in_settings(Settings.model_validate(_lower(SIGN_IN_ENV))) == ()
    blank = {**_lower(SIGN_IN_ENV), "google_client_secret": " ", "database_url": ""}
    assert routes.missing_sign_in_settings(Settings.model_validate(blank)) == (
        "GOOGLE_CLIENT_SECRET",
        "DATABASE_URL",
    )


def test_the_provider_is_not_built_while_sign_in_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, sign_in_env: None
) -> None:
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET")
    get_settings.cache_clear()
    app = _app()
    response = _client(app).get("/auth/callback", params={"code": CODE, "state": "s"})
    assert response.status_code == 503
    assert getattr(app.state, "identity_provider", None) is None
    assert getattr(app.state, "user_repo", None) is None


# --- lazy edges: nothing at import, the real ones on first use -----------------------------


def test_the_real_provider_is_built_on_first_use_and_cached(sign_in_env: None) -> None:
    app = _app()
    config = routes.sign_in_config(get_settings())
    assert config is not None
    provider = routes.get_identity_provider(_request(app), config)
    assert isinstance(provider, GoogleIdentityProvider)
    assert app.state.identity_provider is provider
    assert routes.get_identity_provider(_request(app), config) is provider


def test_an_injected_provider_is_used_as_is(h: Harness) -> None:
    config = routes.sign_in_config(get_settings())
    assert config is not None
    assert routes.get_identity_provider(_request(h.app), config) is h.fake


def _sign_in_through(browser: Browser, fake: FakeIdentityProvider, now: datetime) -> Reply:
    """Log in and come back from Google on an app built without the `h` fixture."""
    browser.get("/auth/login")
    attempt = verify_round_trip(
        browser.cookies[ROUND_TRIP_COOKIE], secret=SecretStr(SESSION_SECRET), now=now
    )
    assert attempt is not None
    fake.claims_by_code[CODE] = fake_claims(nonce=attempt.nonce, aud=CLIENT_ID)
    return browser.get("/auth/callback", params={"code": CODE, "state": attempt.state})


def test_the_real_user_repo_is_built_on_first_use_with_its_schema(
    monkeypatch: pytest.MonkeyPatch, sign_in_env: None, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'users.db'}")
    get_settings.cache_clear()
    app = _app()
    fake = FakeIdentityProvider({})
    app.state.identity_provider = fake
    app.state.clock = Clock()
    response = _sign_in_through(Browser(_client(app)), fake, NOW)
    assert response.status_code == 302, response.text
    repo = app.state.user_repo
    assert isinstance(repo, SqlUserRepo)
    try:
        assert user_count(repo.engine) == 1
    finally:
        repo.engine.dispose()


def test_the_default_clock_is_timezone_aware_utc(sign_in_env: None, engine: Engine) -> None:
    """No `app.state.clock`: the route falls back to UTC now. A naive default would raise in
    the cookie check (aware `exp` against naive `now`) and the callback would not be a 302."""
    app = _app()
    fake = FakeIdentityProvider({})
    app.state.identity_provider = fake
    app.state.user_repo = SqlUserRepo(engine=engine)
    browser = Browser(_client(app))
    real_now = datetime.now(UTC)
    response = _sign_in_through(browser, fake, real_now)
    assert response.status_code == 302, response.text
    session = verify_session(
        browser.cookies[SESSION_COOKIE], secret=SecretStr(SESSION_SECRET), now=real_now
    )
    assert session is not None
    assert abs(session.expires_at - (real_now + SESSION_TTL)) < timedelta(minutes=1)


def test_importing_the_routes_builds_no_settings() -> None:
    """With the sign-in names unset and a setting that cannot parse, any `Settings()` built at
    import (directly or through `get_settings()`) would raise; the cache stays empty too."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "MAX_CONCURRENT_SPECIALISTS": "not-a-number",
    }
    code = (
        "from receipts.settings import get_settings\n"
        "import receipts.auth.routes\n"
        "assert get_settings.cache_info().currsize == 0, 'settings were read at import'\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0, proc.stderr
