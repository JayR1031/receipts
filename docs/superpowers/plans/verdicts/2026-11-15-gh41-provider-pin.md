# Verdict: gh41 provider-pin (head 0ebc6ef, base 7f72a15)

| # | Severity | Finding | Citation |
|---|---|---|---|
| - | none | No HIGH, MEDIUM or LOW findings. | see checks |

Checks
1. Scope: `git diff --name-only 7f72a15...0ebc6ef` = `tests/test_auth_provider.py` only; `git diff -- src/` is 0 bytes; 13 insertions, 0 deletions.
2. Exit command: bin/jig exit 0 (format, lint, types, tests all ok); `pytest tests/test_auth_provider.py -q -rs` exit 0, 69 passed of 69, no skips.
3. Sabotage A (drop `TypeError` from the except at `src/receipts/auth/provider.py:192`, in `_rsa_keys`): exit 1, 1 failed, 68 passed; failing test `test_a_key_set_that_cannot_be_used_is_refused[key-type-as-a-list]`. Reverted; `git diff --exit-code -- src/` exit 0.
4. Sabotage B (`provider.py:94` `kid: NonEmpty` to `str`): exit 1, 1 failed, 68 passed; failing test `test_an_empty_kid_is_rejected_without_a_refetch`. Reverted; exit 0.
5. Synthetic and offline: added lines contain 0 `@` and 0 `AsyncClient` occurrences; the tests reuse the existing fake-transport fixtures. The `kty: ["RSA"]` value is a synthetic key.
6. `uv run pyright tests/test_auth_provider.py`: 0 errors, 0 warnings, 0 informations.
7. Claims: all implementer claims reproduced (69 of 69, 13 insertions, both sabotages red).
8. Both accepted items from the provider verdict (finding 1 MEDIUM, finding 3 LOW) now have a test that fails without the guard.

Sabotages red: A yes, B yes. `git status --porcelain` empty at finish.

VERDICT: PASS
