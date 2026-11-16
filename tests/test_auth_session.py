"""Issue #41 `oidc`: the signed session and OAuth round-trip cookies (ADR-0008).

Synthetic values only: user id `u-0001`, `SecretStr("not-a-real-secret")`. The decoded payloads
are read here without verifying the signature, to show what a browser holding the cookie sees.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from joserfc import jwt
from joserfc.jwk import OctKey
from pydantic import SecretStr
from starlette.responses import Response

from receipts.auth.models import SessionUser
from receipts.auth.oidc import OAuthRoundTrip
from receipts.auth.session import (
    COOKIE_FLAGS,
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
from receipts.settings import Settings, get_settings

SECRET_VALUE = "not-a-real-secret"
SECRET = SecretStr(SECRET_VALUE)
OTHER_SECRET = SecretStr("another-not-real-secret")
NOW = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
USER = SessionUser(user_id="u-0001", expires_at=NOW + SESSION_TTL)
VALUES = OAuthRoundTrip(
    state="fake-state-0001",
    nonce="fake-nonce-0001",
    code_verifier="dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
)
EMAIL = "user@example.com"


def _session() -> str:
    return sign_session(USER, secret=SECRET)


def _round_trip() -> str:
    return sign_round_trip(VALUES, secret=SECRET, now=NOW)


def _segment(token: str, index: int) -> dict[str, object]:
    """Decode one JWT segment without checking the signature."""
    part = token.split(".")[index]
    data = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
    assert isinstance(data, dict)
    return data


def _encode(data: object) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def _change_one_character(token: str, index: int) -> str:
    """Change the first character of segment `index` (header, payload or signature).

    The first character, not the last: the last character of a base64url segment can carry
    padding bits a decoder ignores, so changing it may leave the decoded bytes the same.
    """
    parts = token.split(".")
    first = parts[index][0]
    parts[index] = ("B" if first == "A" else "A") + parts[index][1:]
    return ".".join(parts)


def _with_payload(token: str, payload: dict[str, object]) -> str:
    """Swap in another payload and keep the original header and signature."""
    header, _, signature = token.split(".")
    return ".".join([header, _encode(payload), signature])


def _signed(claims: dict[str, object], *, alg: str = "HS256", secret: str = SECRET_VALUE) -> str:
    """A token we did not issue through `session.py`, signed with our secret all the same."""
    return jwt.encode({"alg": alg}, claims, OctKey.import_key(secret), algorithms=[alg])


def _garbage(exp: int) -> list[object]:
    """Malformed or foreign tokens; each must verify to `None`, whichever kind is expected."""
    unsigned = _encode({"alg": "none", "typ": "JWT"}) + "." + _encode({"uid": "u-0001", "exp": exp})
    cases = {
        "empty": "",
        "one-word": "garbage",
        "three-words": "a.b.c",
        "only-dots": "...",
        "non-ascii": "é.é.é",
        "ten-thousand-chars": "x" * 10_000,
        "alg-none-unsigned": unsigned + ".",
        "hs512-our-secret": _signed({"uid": "u-0001", "exp": exp}, alg="HS512"),
        "extra-email-claim": _signed({"uid": "u-0001", "exp": exp, "email": EMAIL}),
        "no-exp": _signed({"uid": "u-0001"}),
        "empty-uid": _signed({"uid": "", "exp": exp}),
        "exp-as-text": _signed({"uid": "u-0001", "exp": str(exp)}),
        "round-trip-missing-verifier": _signed({"state": "s", "nonce": "n", "exp": exp}),
        "only-exp": _signed({"exp": exp}),
    }
    return [pytest.param(token, id=name) for name, token in cases.items()]


# --- constants -------------------------------------------------------------------------------


def test_lifetimes_and_cookie_names() -> None:
    assert SESSION_TTL == timedelta(days=7)
    assert ROUND_TRIP_TTL == timedelta(minutes=10)
    assert SESSION_MAX_AGE == 7 * 24 * 60 * 60
    assert ROUND_TRIP_MAX_AGE == 10 * 60
    assert SESSION_COOKIE == "receipts_session"
    assert ROUND_TRIP_COOKIE == "receipts_oauth"


def test_cookie_flags_set_httponly_secure_samesite_lax_and_path_root() -> None:
    assert COOKIE_FLAGS == {"path": "/", "secure": True, "httponly": True, "samesite": "lax"}
    response = Response()
    response.set_cookie(SESSION_COOKIE, "value", max_age=SESSION_MAX_AGE, **COOKIE_FLAGS)
    header = response.headers["set-cookie"]
    for attribute in ("HttpOnly", "Secure", "SameSite=lax", "Path=/", "Max-Age=604800"):
        assert attribute in header


# --- the session cookie ----------------------------------------------------------------------


def test_a_signed_session_verifies_to_an_equal_user() -> None:
    assert verify_session(_session(), secret=SECRET, now=NOW) == USER


def test_new_session_ends_seven_days_on_and_survives_the_round_trip() -> None:
    now = NOW + timedelta(microseconds=999_999)
    user = new_session("u-0001", now=now)
    assert user.user_id == "u-0001"
    assert user.expires_at == NOW + SESSION_TTL
    assert verify_session(sign_session(user, secret=SECRET), secret=SECRET, now=now) == user


@pytest.mark.parametrize("index", [0, 1, 2], ids=["header", "payload", "signature"])
def test_a_session_with_one_changed_character_verifies_to_none(index: int) -> None:
    token = _change_one_character(_session(), index)
    assert verify_session(token, secret=SECRET, now=NOW) is None


def test_a_session_whose_payload_names_another_user_verifies_to_none() -> None:
    token = _session()
    forged = _with_payload(token, {**_segment(token, 1), "uid": "u-0002"})
    assert verify_session(forged, secret=SECRET, now=NOW) is None


@pytest.mark.parametrize(
    "now",
    [USER.expires_at, USER.expires_at + timedelta(seconds=1), USER.expires_at + timedelta(days=1)],
    ids=["exp-equals-now", "one-second-after", "one-day-after"],
)
def test_an_expired_session_verifies_to_none(now: datetime) -> None:
    assert verify_session(_session(), secret=SECRET, now=now) is None


def test_a_session_with_one_second_left_still_verifies() -> None:
    now = USER.expires_at - timedelta(seconds=1)
    assert verify_session(_session(), secret=SECRET, now=now) == USER


def test_a_session_signed_with_another_secret_verifies_to_none() -> None:
    token = sign_session(USER, secret=OTHER_SECRET)
    assert verify_session(token, secret=SECRET, now=NOW) is None


@pytest.mark.parametrize("token", _garbage(int(USER.expires_at.timestamp())))
def test_a_garbage_session_verifies_to_none(token: str) -> None:
    assert verify_session(token, secret=SECRET, now=NOW) is None


def test_a_round_trip_cookie_is_not_a_session() -> None:
    assert verify_session(_round_trip(), secret=SECRET, now=NOW) is None


def test_the_session_payload_carries_only_the_user_id_and_expiry() -> None:
    token = _session()
    assert _segment(token, 0) == {"alg": "HS256", "typ": "JWT"}
    payload = _segment(token, 1)
    assert payload == {"uid": "u-0001", "exp": int((NOW + SESSION_TTL).timestamp())}
    assert "email" not in payload
    assert EMAIL not in json.dumps(payload)
    assert SECRET_VALUE not in token


def test_signing_with_an_empty_secret_is_refused() -> None:
    with pytest.raises(ValueError) as excinfo:
        sign_session(USER, secret=SecretStr(""))
    assert SECRET_VALUE not in str(excinfo.value)


def test_verifying_with_an_empty_secret_is_none() -> None:
    assert verify_session(_session(), secret=SecretStr(""), now=NOW) is None


# --- the OAuth round-trip cookie -------------------------------------------------------------


def test_a_signed_round_trip_verifies_to_equal_values() -> None:
    assert verify_round_trip(_round_trip(), secret=SECRET, now=NOW) == VALUES


def test_a_round_trip_with_one_second_left_still_verifies() -> None:
    now = NOW + ROUND_TRIP_TTL - timedelta(seconds=1)
    assert verify_round_trip(_round_trip(), secret=SECRET, now=now) == VALUES


@pytest.mark.parametrize(
    "now",
    [NOW + ROUND_TRIP_TTL, NOW + ROUND_TRIP_TTL + timedelta(seconds=1), NOW + timedelta(days=1)],
    ids=["exp-equals-now", "one-second-after", "one-day-after"],
)
def test_an_expired_round_trip_verifies_to_none(now: datetime) -> None:
    assert verify_round_trip(_round_trip(), secret=SECRET, now=now) is None


@pytest.mark.parametrize("index", [0, 1, 2], ids=["header", "payload", "signature"])
def test_a_round_trip_with_one_changed_character_verifies_to_none(index: int) -> None:
    token = _change_one_character(_round_trip(), index)
    assert verify_round_trip(token, secret=SECRET, now=NOW) is None


def test_a_round_trip_with_another_state_verifies_to_none() -> None:
    token = _round_trip()
    forged = _with_payload(token, {**_segment(token, 1), "state": "attacker-state"})
    assert verify_round_trip(forged, secret=SECRET, now=NOW) is None


def test_a_round_trip_signed_with_another_secret_verifies_to_none() -> None:
    token = sign_round_trip(VALUES, secret=OTHER_SECRET, now=NOW)
    assert verify_round_trip(token, secret=SECRET, now=NOW) is None


@pytest.mark.parametrize("token", _garbage(int((NOW + ROUND_TRIP_TTL).timestamp())))
def test_a_garbage_round_trip_verifies_to_none(token: str) -> None:
    assert verify_round_trip(token, secret=SECRET, now=NOW) is None


def test_a_session_cookie_is_not_a_round_trip() -> None:
    assert verify_round_trip(_session(), secret=SECRET, now=NOW) is None


def test_the_round_trip_payload_carries_only_the_attempt_and_its_expiry() -> None:
    token = _round_trip()
    payload = _segment(token, 1)
    assert payload == {
        "state": VALUES.state,
        "nonce": VALUES.nonce,
        "code_verifier": VALUES.code_verifier,
        "exp": int((NOW + ROUND_TRIP_TTL).timestamp()),
    }
    assert "email" not in payload
    assert EMAIL not in json.dumps(payload)
    assert SECRET_VALUE not in token


# --- the two sign-in secrets in Settings (carried from the `contract` judge) -----------------


LIVE_NAMES = (
    "ANTHROPIC_API_KEY",
    "KEENABLE_API_KEY",
    "DATABASE_URL",
    "DEMO_PASSCODE",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "SESSION_SECRET",
)


@pytest.fixture
def fresh_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """No live value in the environment, so a failing assertion cannot print one."""
    for name in LIVE_NAMES:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize(
    ("name", "read"),
    [
        ("GOOGLE_CLIENT_SECRET", lambda s: s.google_client_secret),
        ("SESSION_SECRET", lambda s: s.session_secret),
    ],
    ids=["google_client_secret", "session_secret"],
)
def test_the_sign_in_secrets_are_secret_str_and_hide_their_value(
    fresh_settings: None,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    read: Callable[[Settings], SecretStr | None],
) -> None:
    synthetic = f"synthetic-{name.lower()}-0001"
    monkeypatch.setenv(name, synthetic)
    for settings in (Settings(), get_settings()):
        value = read(settings)
        assert isinstance(value, SecretStr)
        assert value == SecretStr(synthetic)
        for shown in (repr(value), str(value), repr(settings), str(settings)):
            assert synthetic not in shown
