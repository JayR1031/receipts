# Verdict: gh41 gate-docstring-2 (head 1029451, base 3253fe2)

| # | Severity | Finding | Citation |
|---|---|---|---|
| 1 | LOW | The pyright exit code was captured behind a pipe to `tail`, so `$?` is tail's. The output line `0 errors, 0 warnings, 0 informations` is the evidence. | `uv run pyright src/receipts/auth` |
| 2 | LOW | uv warned that `VIRTUAL_ENV` does not match the project environment. This is harmless. | pyright run |

No HIGH or MEDIUM findings.

Checks
1. Scope: `git diff --name-only 3253fe2...1029451` printed only `src/receipts/auth/gate.py` (exit 0).
2. Docstring only: the diff is one hunk, `@@ -31,8 +31,9 @@`. It changes the 2 docstring lines at `gate.py:34-35` and adds 1. No code lines changed.
3. Exit command: `bin/jig` exited 0. The table is python format ok, lint ok, types ok, tests ok. `grep -n MissingSettingError` exited 1 (no match), so `!` passes. The `.venv` was present and the env vars were unset.
4. Docstring against code. `gate.py:32-36` reads: "A refusal raises `PermissionError` whose message is the `StartDecision.reason`. A missing required setting (the Keenable key) also raises `PermissionError`, its message naming the variable and never its value. No run starts either way."
   - `wiring.py:430-435` (`_require_key`) catches `MissingSettingError` and raises `PermissionError(f"{exc.name} is not set") from exc`. That carries the variable name only.
   - `wiring.py:505-506` (`LiveGate.start`) raises `PermissionError(decision.reason)` on refusal, then calls `_require_key(settings)`.
   - The docstring matches the code. The ordering of the key check after the start rule is not documented, but the brief did not ask for it.
5. `uv run pyright src/receipts/auth` printed 0 errors, 0 warnings, 0 informations.
6. `grep -c MissingSettingError src/receipts/auth/gate.py` printed 0.
7. `git status --porcelain` was empty after the checks, with nothing created in the worktree.

Watched-failing (rubric 3) does not apply: docstring-only change, and the exit command's `! grep` is the check.

VERDICT: PASS
