# Verdict: gh45 `dedupe-docstrings` (judge, fresh context, 2026-11-18)

Reviewed: branch `jay/gh-45-dedupe-docstrings` at `62370e0`, diff `1c3e127...HEAD` (one commit). Saved by the orchestrator from the judge's final message; gate evidence condensed, the finding verbatim.

VERDICT: PASS

Only the two module docstrings changed, the exit command exits 0, and both docstrings now say all four required things in a way that matches the code and ADR-0007 line 18. One LOW finding; no HIGH, CRITICAL or MEDIUM.

## Gate items (condensed; every item passed)

1. **Scope.** `git diff --name-only 1c3e127...HEAD`: `src/receipts/harness/repair.py`, `src/receipts/harness/specialist.py`; one hunk each (`@@ -22,3 +22,5 @@`, `@@ -19,2 +19,4 @@`), inside the module docstrings (lines 1-33 and 1-28 at head). AST comparison of base against head: every top-level node after the module docstring equal (31 of 31 in `repair.py`, 49 of 49 in `specialist.py`); every source line after the docstring identical (197 and 454 lines), comments included. Line numbers below the docstring moved by 2 (`_accepted_repairs(...)` now called at `specialist.py:425`).
2. **Exit.** The exit command exit 0; jig format, lint, types, tests `ok`; `tests/test_harness_repair.py` 18 of 18 passed; full unit suite (`-m "not integration" -rs`, seven variables unset) 692 passed, 14 deselected, 0 skipped, exit 0.
3. **LOW 1 and LOW 2 of the `dedupe` verdict closed.** `second claim|put a second|cannot back|one piece of evidence` grep exit 1 on both files and repo-wide. Each of the four statements (copy refused; original to the Verifier unchanged; keeps-own accepted even when another agent-written claim cites it; agent-written claims on one receipt all count) appears in both docstrings (`repair.py:22-26`, `specialist.py:18-22`) and is backed by code (`specialist.py:283-285`, `:298-307`, `:316`, `:449`) and tests (`tests/test_harness_repair.py:289-296`, `:335-336`, `:354-358`). Rule then exception, as ADR-0007 line 18.
4. **Nothing new is wrong.** Every changed sentence checked against the code; "another claim the agent wrote" hides no other case (`:285`, `:305`); "identical" was already the base wording and ADR-0007 line 18 defines it as the code does (`specialist.py:262-269`).

## Finding (verbatim)

| # | Severity | Finding | Citation | Fix |
|---|---|---|---|---|
| 1 | LOW | Read on its own, the rule sentence in each docstring is still unqualified. It says the runner "does not accept a repair whose receipt is identical to another of the specialist's claims' receipts". The code accepts exactly such a repair when it keeps its own original receipt. The next sentence states that exception, in the same rule-then-exception form as ADR-0007 line 18, so `dedupe` LOW 1 and LOW 2 stay closed. But anyone who quotes the first sentence alone gets the rule wrong. | Rule sentences: `src/receipts/harness/repair.py:22-23` and `src/receipts/harness/specialist.py:18-19`. Contrary code: `specialist.py:283-284`. Test: `tests/test_harness_repair.py:335-336` | Put the exception inside the rule sentence: "...identical to another of the specialist's claims' receipts, unless it keeps its own claim's original receipt," |

VERDICT: PASS

## Orchestrator disposition (2026-11-18)

Finding 1 is accepted as a LOW, not acted on: the pair of sentences is accurate, follows ADR-0007 line 18's rule-then-exception form, and the judge confirms the `dedupe` LOWs are closed. Recorded for the whole-PR judge.
