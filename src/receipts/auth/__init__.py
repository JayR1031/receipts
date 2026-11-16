"""Optional Google sign-in, sessions and daily run limits (lane L7, issue #41, ADR-0008).

`models` holds the frozen shared types; `gate` holds the `Gate` protocol, the only way identity
reaches the UI. Nothing in this package reads a setting at import.
"""

from receipts.auth.gate import Gate
from receipts.auth.models import (
    AccountStatus,
    AuthError,
    IdTokenClaims,
    SessionUser,
    StartDecision,
    User,
)

__all__ = [
    "AccountStatus",
    "AuthError",
    "Gate",
    "IdTokenClaims",
    "SessionUser",
    "StartDecision",
    "User",
]
