"""`/auth/*`: optional "Sign in with Google" (issue #41, ADR-0008). Handlers stay thin.

- `GET /auth/login` starts one sign-in attempt: a fresh state, nonce and PKCE verifier go into
  the signed round-trip cookie (10 minutes) and the browser is sent (302) to Google's
  authorization endpoint for `openid email`. A request on `127.0.0.1` is first sent to
  `http://localhost:8000/auth/login`: the round-trip cookie is host-only and `callback_url` sends
  both local hosts back to `localhost`, so a cookie set on `127.0.0.1` would never return.
- `GET /auth/callback` finishes it, in this order: the round-trip cookie must verify; `state`
  must equal the cookie's (constant time; present is not enough); the provider swaps the code
  for the ID token's signature-verified claims; `validate_claims` checks issuer, audience,
  expiry and nonce against this attempt and the clock. Only then is the `users` row read or
  created (`sub` and `email`, nothing else) and the session cookie (our user id and its expiry,
  7 days) set; the round-trip cookie is cleared and the browser goes (302) to `/ui`. Every
  failure is 400 with the detail `sign-in check failed: <check>`, naming the check and never a
  value; it sets no session cookie and writes no row. A failure after the round-trip cookie
  verified also clears that cookie, so an attempt is not retried with the same values.
- `POST /auth/logout` clears the session cookie and answers 303 See Other to `/ui`: 303, so the
  browser follows with a GET whatever the form's method (Starlette's default 307 would repeat
  the POST). It needs no CSRF token: all it does is clear a cookie, and the worst a forged
  logout can do is sign someone out. Sessions are stateless signed cookies, so logout clears
  the browser's copy; a copy taken earlier stays valid until its expiry.
- `GET /auth/me` is `{"email": ...}` for a valid session whose user still exists, else 401.

Modes. Sign-in needs four settings: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET`
and `DATABASE_URL` (unset or blank counts as missing, as in `receipts.api.wiring`). With any
missing, `/auth/login` and `/auth/callback` answer 503 naming the first one in that order, never
a value, before anything is signed (signing refuses an empty secret) or built (the client secret
may be `None`), and `current_user` is `None` for every request.

Edges, read per request from `app.state`: `identity_provider` (an `IdentityProvider`),
`user_repo` (a `SqlUserRepo`) and `clock` (a `Callable[[], datetime]` returning a timezone-aware
time; default UTC now). The wiring or a test sets them. When the provider or the repo is absent,
the real one is built on the first request that needs it after the availability check, and
cached on `app.state`; never at import or in `create_app()`. A repo built here also runs
`create_schema` once, so the `users` table exists on a fresh database. Two first requests at
once may each build one; the last one cached wins, and both schema runs are idempotent.

Settings are read per request through `get_settings()`. Nothing here logs.
`get_secret_value()` is called only in `_is_set`, which returns a bool.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, cast

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, SecretStr

from receipts.api.models import ErrorDetail
from receipts.auth.models import AuthError, SessionUser, User
from receipts.auth.oidc import (
    CALLBACK_PATH,
    LOCAL_CALLBACK_URL,
    OAuthRoundTrip,
    authorization_url,
    callback_url,
    code_challenge,
    new_round_trip,
    validate_claims,
)
from receipts.auth.provider import GoogleIdentityProvider, IdentityProvider
from receipts.auth.session import (
    COOKIE_FLAGS,
    ROUND_TRIP_COOKIE,
    ROUND_TRIP_MAX_AGE,
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    new_session,
    sign_round_trip,
    sign_session,
    verify_round_trip,
    verify_session,
)
from receipts.db.repo import create_schema
from receipts.db.users import SqlUserRepo
from receipts.settings import Settings, get_settings

__all__ = [
    "Clock",
    "SIGN_IN_NAMES",
    "Me",
    "SignInConfig",
    "current_user",
    "get_clock",
    "get_identity_provider",
    "get_user_repo",
    "missing_sign_in_settings",
    "router",
    "sign_in_config",
]

router = APIRouter(prefix="/auth", tags=["auth"])

Clock = Callable[[], datetime]

LOGIN_PATH: Final = "/auth/login"
# Where the browser lands after sign-in and logout: the Gradio UI (`receipts.ui.app.UI_PATH`).
UI_PATH: Final = "/ui"
# The registered local callback is on `localhost:8000`, so local sign-in starts there too.
LOCAL_LOGIN_URL: Final = LOCAL_CALLBACK_URL.removesuffix(CALLBACK_PATH) + LOGIN_PATH
_LOOPBACK_IP: Final = "127.0.0.1"
SIGN_IN_NAMES: Final = (
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "SESSION_SECRET",
    "DATABASE_URL",
)


class Me(BaseModel):
    """`GET /auth/me`: the signed-in person's email, the only profile value we keep besides
    Google's subject id."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str


@dataclass(frozen=True)
class SignInConfig:
    """The three values sign-in uses, present and non-blank. `DATABASE_URL` is checked too but
    read by the repo itself."""

    client_id: str
    client_secret: SecretStr
    session_secret: SecretStr


def _is_set(value: SecretStr | str | None) -> bool:
    text = value.get_secret_value() if isinstance(value, SecretStr) else value
    return bool(text and text.strip())


def missing_sign_in_settings(settings: Settings) -> tuple[str, ...]:
    """The names (never the values) of the sign-in settings that are unset or blank, in the
    order `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET`, `DATABASE_URL`."""
    values = (
        settings.google_client_id,
        settings.google_client_secret,
        settings.session_secret,
        settings.database_url,
    )
    return tuple(
        name for name, value in zip(SIGN_IN_NAMES, values, strict=True) if not _is_set(value)
    )


def sign_in_config(settings: Settings) -> SignInConfig | None:
    """The sign-in values, or `None` when any of the four settings is missing."""
    client_id = settings.google_client_id
    client_secret = settings.google_client_secret
    session_secret = settings.session_secret
    if missing_sign_in_settings(settings) or not (client_id and client_secret and session_secret):
        return None
    return SignInConfig(client_id, client_secret, session_secret)


def _availability(settings: Settings) -> SignInConfig:
    """503 naming the first missing sign-in setting, like `check_keenable_key`; never a value."""
    config = sign_in_config(settings)
    if config is None:
        name = missing_sign_in_settings(settings)[0]
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"{name} is not set")
    return config


def _utc_now() -> datetime:
    return datetime.now(UTC)


def get_clock(request: Request) -> Clock:
    """`app.state.clock` when set (tests), else UTC now. Either way the time is aware."""
    configured: object = getattr(request.app.state, "clock", None)
    if callable(configured):
        return cast(Clock, configured)
    return _utc_now


def get_identity_provider(request: Request, config: SignInConfig) -> IdentityProvider:
    """`app.state.identity_provider`, or the real Google provider, built once and cached there."""
    state = request.app.state
    configured: object = getattr(state, "identity_provider", None)
    if configured is None:
        configured = GoogleIdentityProvider(config.client_id, config.client_secret)
        state.identity_provider = configured
    # `IdentityProvider` is a Protocol without runtime checks; `app.state` is untyped. The
    # wiring, a test or the line above is the only writer of this attribute.
    return cast(IdentityProvider, configured)


async def get_user_repo(request: Request) -> SqlUserRepo:
    """`app.state.user_repo`, or a `SqlUserRepo` on `DATABASE_URL` whose schema is created once,
    then cached there. An injected repo's schema is its owner's business."""
    state = request.app.state
    configured: object = getattr(state, "user_repo", None)
    if configured is not None:
        return cast(SqlUserRepo, configured)
    repo = SqlUserRepo()
    await create_schema(repo.engine)
    state.user_repo = repo
    return repo


def current_user(request: Request, settings: Settings, clock: Clock) -> SessionUser | None:
    """The user in a valid session cookie, or `None`: no cookie, sign-in not configured, or a
    tampered, expired or foreign cookie. Reads no database, so a session whose user was deleted
    is still returned (`/auth/me` checks the row). For the wiring's `Gate.identify`."""
    config = sign_in_config(settings)
    token = request.cookies.get(SESSION_COOKIE)
    if config is None or token is None:
        return None
    return verify_session(token, secret=config.session_secret, now=clock())


def _host(request: Request) -> str:
    """The request's `Host` (name and port), which `callback_url` maps to a registered URI."""
    return request.url.netloc


def _start_login(request: Request, config: SignInConfig, now: datetime) -> RedirectResponse:
    attempt = new_round_trip()
    url = authorization_url(
        client_id=config.client_id,
        redirect_uri=callback_url(_host(request)),
        state=attempt.state,
        nonce=attempt.nonce,
        code_challenge=code_challenge(attempt.code_verifier),
    )
    response = RedirectResponse(url, status_code=status.HTTP_302_FOUND)
    token = sign_round_trip(attempt, secret=config.session_secret, now=now)
    response.set_cookie(ROUND_TRIP_COOKIE, token, max_age=ROUND_TRIP_MAX_AGE, **COOKIE_FLAGS)
    return response


def _attempt(request: Request, config: SignInConfig, now: datetime) -> OAuthRoundTrip | None:
    token = request.cookies.get(ROUND_TRIP_COOKIE)
    if token is None:
        return None
    return verify_round_trip(token, secret=config.session_secret, now=now)


def _same_state(expected: str, received: str | None) -> bool:
    """Equal, in constant time on UTF-8 bytes; a missing `state` is never equal."""
    return received is not None and secrets.compare_digest(expected.encode(), received.encode())


async def _finish_login(
    request: Request,
    config: SignInConfig,
    attempt: OAuthRoundTrip,
    *,
    code: str | None,
    state: str | None,
    now: datetime,
) -> User:
    """The signed-in user. Raises `AuthError` naming the first failed check: `state`, `code`,
    the provider's (`token_exchange`, `jwks`, `id_token`) or `validate_claims`' (`iss`, `aud`,
    `exp`, `nonce`). Nothing is written before every check has passed."""
    if not _same_state(attempt.state, state):
        raise AuthError("state")
    if not code:
        raise AuthError("code")
    provider = get_identity_provider(request, config)
    claims = await provider.exchange(
        code, redirect_uri=callback_url(_host(request)), code_verifier=attempt.code_verifier
    )
    valid = validate_claims(claims, client_id=config.client_id, nonce=attempt.nonce, now=now)
    repo = await get_user_repo(request)
    return await repo.get_or_create(valid.sub, valid.email, now)


def _set_session(response: Response, user: User, config: SignInConfig, now: datetime) -> None:
    token = sign_session(new_session(user.id, now=now), secret=config.session_secret)
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_MAX_AGE, **COOKIE_FLAGS)


def _refused(check: str, *, clear_round_trip: bool) -> JSONResponse:
    """400 in FastAPI's error shape, naming the failed check only."""
    response = JSONResponse(
        {"detail": f"sign-in check failed: {check}"}, status_code=status.HTTP_400_BAD_REQUEST
    )
    if clear_round_trip:
        response.delete_cookie(ROUND_TRIP_COOKIE, **COOKIE_FLAGS)
    return response


_REFUSED: Final = {"model": ErrorDetail, "description": "A sign-in check failed; names it."}
_UNAVAILABLE: Final = {"model": ErrorDetail, "description": "Sign-in is not configured."}


@router.get(
    "/login",
    status_code=status.HTTP_302_FOUND,
    response_class=RedirectResponse,
    responses={503: _UNAVAILABLE},
)
async def login(request: Request) -> RedirectResponse:
    config = _availability(get_settings())
    if request.url.hostname == _LOOPBACK_IP:
        return RedirectResponse(LOCAL_LOGIN_URL, status_code=status.HTTP_302_FOUND)
    return _start_login(request, config, get_clock(request)())


@router.get(
    "/callback",
    status_code=status.HTTP_302_FOUND,
    response_class=RedirectResponse,
    responses={400: _REFUSED, 503: _UNAVAILABLE},
)
async def callback(request: Request, code: str | None = None, state: str | None = None) -> Response:
    config = _availability(get_settings())
    now = get_clock(request)()
    attempt = _attempt(request, config, now)
    if attempt is None:
        return _refused("round_trip", clear_round_trip=False)
    try:
        user = await _finish_login(request, config, attempt, code=code, state=state, now=now)
    except AuthError as exc:
        return _refused(exc.check, clear_round_trip=True)
    response = RedirectResponse(UI_PATH, status_code=status.HTTP_302_FOUND)
    _set_session(response, user, config, now)
    response.delete_cookie(ROUND_TRIP_COOKIE, **COOKIE_FLAGS)
    return response


@router.post("/logout", status_code=status.HTTP_303_SEE_OTHER, response_class=RedirectResponse)
async def logout() -> RedirectResponse:
    response = RedirectResponse(UI_PATH, status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE, **COOKIE_FLAGS)
    return response


@router.get("/me", response_model=Me, responses={401: {"model": ErrorDetail}})
async def me(request: Request, response: Response) -> Me:
    session = current_user(request, get_settings(), get_clock(request))
    user = None if session is None else await (await get_user_repo(request)).get(session.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not signed in")
    response.headers["Cache-Control"] = "no-store"  # a personal answer; no cache keeps it
    return Me(email=user.email)
