"""Lane L2: pure claim verification against fetched pages and the search log. Owned by L2.

See `receipts.verify.rules` for the rules and the dropped-claim convention.
"""

from receipts.verify.rules import (
    DROPPED_PREFIX,
    FUZZY_THRESHOLD,
    NOTE_FETCH_FAILED,
    NOTE_QUERY_NOT_LOGGED,
    NOTE_URL_NOT_FETCHED,
    dropped_reason,
    is_dropped,
    normalize,
    verify_all,
    verify_claim,
)

__all__ = [
    "DROPPED_PREFIX",
    "FUZZY_THRESHOLD",
    "NOTE_FETCH_FAILED",
    "NOTE_QUERY_NOT_LOGGED",
    "NOTE_URL_NOT_FETCHED",
    "dropped_reason",
    "is_dropped",
    "normalize",
    "verify_all",
    "verify_claim",
]
