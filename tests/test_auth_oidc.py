"""Issue #41 `oidc`: the pure OpenID Connect checks and builders (ADR-0008).

Synthetic values only: `fake-sub-0001`, `user@example.com`, `client-id-not-real`. No network,
no clock: every time is the fixed `NOW` below.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import ValidationError

from receipts.auth.models import AuthError, IdTokenClaims
from receipts.auth.oidc import (
    OAuthRoundTrip,
    authorization_url,
    callback_url,
    code_challenge,
    new_code_verifier,
    new_nonce,
    new_round_trip,
    new_state,
    validate_claims,
)

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
CLIENT_ID = "client-id-not-real"
NONCE = "fake-nonce-0001"
EMAIL = "user@example.com"
LOCAL = "http://localhost:8000/auth/callback"
DEPLOYED = "https://receipts-h745.onrender.com/auth/callback"
# RFC 7636 appendix B: the verifier and the S256 challenge it must produce.
RFC_VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
RFC_CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
# RFC 7636 section 4.1: 43 to 128 characters from the unreserved set.
VERIFIER_SHAPE = re.compile(r"[A-Za-z0-9\-._~]{43,128}")
URL_SAFE_TOKEN = re.compile(r"[A-Za-z0-9\-_]{43,}")


def _claims(**changes: object) -> IdTokenClaims:
    base: dict[str, object] = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "fake-sub-0001",
        "email": EMAIL,
        "exp": NOW + timedelta(minutes=5),
        "nonce": NONCE,
    }
    return IdTokenClaims.model_validate({**base, **changes})


def _check(claims: IdTokenClaims, *, client_id: str = CLIENT_ID, nonce: str = NONCE) -> str:
    """The `check` named by the `AuthError` that `validate_claims` raises."""
    with pytest.raises(AuthError) as excinfo:
        validate_claims(claims, client_id=client_id, nonce=nonce, now=NOW)
    return excinfo.value.check


# --- validate_claims -------------------------------------------------------------------------


@pytest.mark.parametrize("issuer", ["https://accounts.google.com", "accounts.google.com"])
def test_a_valid_claim_set_is_returned_unchanged(issuer: str) -> None:
    claims = _claims(iss=issuer)
    assert validate_claims(claims, client_id=CLIENT_ID, nonce=NONCE, now=NOW) is claims


@pytest.mark.parametrize(
    "issuer",
    [
        "https://accounts.google.com.evil.example",
        "http://accounts.google.com",
        "https://evil.example",
        "accounts.google.com/",
        "",
    ],
)
def test_a_wrong_issuer_fails_the_iss_check(issuer: str) -> None:
    assert _check(_claims(iss=issuer)) == "iss"


@pytest.mark.parametrize("audience", ["other-client-id", f"{CLIENT_ID} ", CLIENT_ID.upper(), ""])
def test_a_wrong_audience_fails_the_aud_check(audience: str) -> None:
    assert _check(_claims(aud=audience)) == "aud"


def test_an_empty_client_id_never_matches_an_empty_audience() -> None:
    assert _check(_claims(aud=""), client_id="") == "aud"


@pytest.mark.parametrize(
    "exp",
    [NOW, NOW - timedelta(seconds=1), NOW - timedelta(days=1)],
    ids=["exp-equals-now", "one-second-ago", "one-day-ago"],
)
def test_an_expired_token_fails_the_exp_check(exp: datetime) -> None:
    """`exp == now` is expired: the token must be valid strictly before its `exp`."""
    assert _check(_claims(exp=exp)) == "exp"


def test_a_token_with_one_second_left_passes() -> None:
    claims = _claims(exp=NOW + timedelta(seconds=1))
    assert validate_claims(claims, client_id=CLIENT_ID, nonce=NONCE, now=NOW) is claims


@pytest.mark.parametrize("token_nonce", ["other-nonce", f"{NONCE}x", NONCE[:-1], "", "nonce-é"])
def test_a_mismatched_nonce_fails_the_nonce_check(token_nonce: str) -> None:
    assert _check(_claims(nonce=token_nonce)) == "nonce"


def test_an_empty_expected_nonce_never_matches_an_empty_token_nonce() -> None:
    """A nonce is compared for equality with the one we sent, never accepted for being present."""
    assert _check(_claims(nonce=""), nonce="") == "nonce"


def test_a_non_ascii_expected_nonce_fails_cleanly() -> None:
    """`secrets.compare_digest` rejects non-ASCII `str`; the check must still be an AuthError."""
    assert _check(_claims(), nonce="nonce-é") == "nonce"


def test_the_error_names_its_check_and_carries_no_claim_value() -> None:
    claims = _claims(nonce="token-nonce-0002")
    with pytest.raises(AuthError) as excinfo:
        validate_claims(claims, client_id=CLIENT_ID, nonce=NONCE, now=NOW)
    message = str(excinfo.value)
    assert "nonce" in message
    for value in (EMAIL, "fake-sub-0001", "token-nonce-0002", NONCE, CLIENT_ID):
        assert value not in message


# --- callback_url ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("localhost:8000", LOCAL),
        ("localhost", LOCAL),
        ("127.0.0.1:8000", LOCAL),
        ("127.0.0.1", LOCAL),
        ("LOCALHOST:8000", LOCAL),
        ("receipts-h745.onrender.com", DEPLOYED),
    ],
)
def test_callback_url_yields_the_two_registered_uris(host: str, expected: str) -> None:
    assert callback_url(host) == expected


@pytest.mark.parametrize("host", ["localhost.example.com", "127.0.0.1.example.com"])
def test_a_host_that_only_starts_like_a_local_one_is_not_local(host: str) -> None:
    assert callback_url(host) == f"https://{host}/auth/callback"


# --- PKCE, state and nonce -------------------------------------------------------------------


def test_code_challenge_matches_the_rfc_7636_appendix_b_vector() -> None:
    assert code_challenge(RFC_VERIFIER) == RFC_CHALLENGE


def test_a_code_verifier_has_the_rfc_7636_shape_and_is_fresh_each_time() -> None:
    first, second = new_code_verifier(), new_code_verifier()
    assert VERIFIER_SHAPE.fullmatch(first)
    assert VERIFIER_SHAPE.fullmatch(second)
    assert first != second


@pytest.mark.parametrize("make", [new_state, new_nonce], ids=["state", "nonce"])
def test_state_and_nonce_are_url_safe_and_fresh_each_time(make: Callable[[], str]) -> None:
    first, second = make(), make()
    assert URL_SAFE_TOKEN.fullmatch(first)
    assert first != second


def test_a_new_round_trip_holds_fresh_values_and_a_verifier_shaped_for_pkce() -> None:
    first, second = new_round_trip(), new_round_trip()
    assert URL_SAFE_TOKEN.fullmatch(first.state)
    assert URL_SAFE_TOKEN.fullmatch(first.nonce)
    assert VERIFIER_SHAPE.fullmatch(first.code_verifier)
    assert len({first.state, first.nonce, first.code_verifier}) == 3
    assert first != second


@pytest.mark.parametrize("field", ["state", "nonce", "code_verifier"])
def test_a_round_trip_refuses_an_empty_value(field: str) -> None:
    values = {"state": "fake-state-0001", "nonce": NONCE, "code_verifier": RFC_VERIFIER}
    with pytest.raises(ValidationError):
        OAuthRoundTrip.model_validate({**values, field: ""})


def test_a_round_trip_is_frozen() -> None:
    values = OAuthRoundTrip(state="fake-state-0001", nonce=NONCE, code_verifier=RFC_VERIFIER)
    with pytest.raises(ValidationError):
        values.state = "other-state"


# --- authorization_url -----------------------------------------------------------------------


def test_the_authorization_url_carries_exactly_the_openid_parameters() -> None:
    url = authorization_url(
        client_id=CLIENT_ID,
        redirect_uri=LOCAL,
        state="fake-state-0001",
        nonce=NONCE,
        code_challenge=RFC_CHALLENGE,
    )
    parts = urlsplit(url)
    assert (parts.scheme, parts.netloc, parts.path) == (
        "https",
        "accounts.google.com",
        "/o/oauth2/v2/auth",
    )
    assert parts.fragment == ""
    assert parse_qs(parts.query, strict_parsing=True) == {
        "response_type": ["code"],
        "client_id": [CLIENT_ID],
        "redirect_uri": [LOCAL],
        "scope": ["openid email"],
        "state": ["fake-state-0001"],
        "nonce": [NONCE],
        "code_challenge": [RFC_CHALLENGE],
        "code_challenge_method": ["S256"],
    }


def test_a_value_with_reserved_characters_cannot_add_a_parameter() -> None:
    url = authorization_url(
        client_id=CLIENT_ID,
        redirect_uri=DEPLOYED,
        state="fake-state&scope=openid+email+profile",
        nonce=NONCE,
        code_challenge=RFC_CHALLENGE,
    )
    query = parse_qs(urlsplit(url).query, strict_parsing=True)
    assert query["state"] == ["fake-state&scope=openid+email+profile"]
    assert query["scope"] == ["openid email"]
    assert query["redirect_uri"] == [DEPLOYED]
