# Plan: GitHub issue #45 — verifier follow-ups (claim values, "free", duplicate repairs, the PR #35 measurement)

Brief: `docs/superpowers/briefs/2026-11-16-gh45-verifier-follow-ups.md`. Standard: `AGENTS.md` and `CLAUDE.md` read from `origin/main` = `949741f` (sections 0 to 5 and 9). Format: the kit's `docs/plan-graph-format.md` (not on `origin/main`; read from `~/Projects/agentic-standard`). Written 2026-11-18 by the orchestrator. **Approved by the owner 2026-11-18 06:16:22 UTC** (relayed by the coordinating session, Claude Code session `477932e0`); answers under "Approval and answers". Dispatch began 2026-11-18 06:17 UTC.

**Where the truth is:** from dispatch on, this file's copy on the integration branch (`.worktrees/gh45/docs/superpowers/plans/2026-11-16-gh45-verifier-follow-ups.md`) is the source of truth; the main checkout's untracked copy is overwritten from it after each state change. A new session reads the integration copy, runs `bin/plan-check <it> --ready`, and proceeds.

Base revision for every fact and every worktree: `origin/main` = `949741fc67920b39d51e3615d051cec9d6e7a440` (deployed, per the coordinating session). Line numbers below are read from that commit with `git show origin/main:<path>`.

## Shape

One ticket, one PR, seven tasks, stitched together on an **integration branch** as #41 was:

- Integration branch `jay/gh-45-verifier-follow-ups` (the brief's suggested name), cut from `949741f`, worktree `.worktrees/gh45`. Its first commit is the brief and this plan (the brief ships with the PR, as #41's did; see "Scope notes" on why the brief's own path is not in its Allowed list). It becomes the single PR against `main`.
- Each task: worktree `.worktrees/gh45-<id>`, branch `jay/gh-45-<id>`, cut from the integration branch's head at dispatch. No existing worktree or branch uses these names (`git worktree list`, `git branch -a --list '*gh-45*'`, both empty for `gh45`).
- On a passing judge verdict the task branch is merged into the integration branch (fast-forward when possible, else a plain merge; never a rebase or force-push), and only then is the task `merged`. **Who does that merge is question 3.** Without delegation, each PASS waits for the owner.
- Dependent tasks are cut only after their dependencies are `merged`, so each sees judged code, not a report of it.
- The last task (`records`) is judged on the **whole** integration-branch diff against `origin/main`, with the brief's full Verification list (1 to 7) after the branch merges `origin/main`. That verdict is the PR's `/judge` verdict. The PR description and the issue #45 comment then go through `/verify-claims` before either is posted.

### Why this order

| Wave | Tasks | Why |
|---|---|---|
| A | `fuzz-port`, `dedupe` (parallel, disjoint scopes) | `fuzz-port` produces the measurement contract (`scripts/verify_fuzz/`, `run_baseline.py`, `expected.txt`) that every rules task is gated on. `dedupe` is lane L1 only (`harness/`, its test, ADR-0007) and shares no file with L2. |
| B | `fuzz-claims` | Extends the same `run_baseline.py` and `expected.txt`, so it is sequential behind `fuzz-port`. Its red-first run (exit 1 on the claim shapes only) must happen while the integration branch still has `949741f`'s `rules.py`, that is, before any rules task lands. |
| C | `token` (d) | Changes `_NUMBER_TOKEN` and `_canonical_number`, the tokenizer that (c) and (a) build on, and the only change that can move the eleven quote-to-page counts. First of the rules chain so its movement is measured alone. |
| D | `unsigned` (c) | Claim-rule-only reading on top of the new tokens. Same files as `token`. |
| E | `counts-free` (a) and (b) | Smallest two rules, both in `_claim_values`/`_quote_values`; after (c) so the unit-count reading does not collide with the unsigned-price reading of a bare integer. Same files. |
| F | `records` | `rules.py` docstring and the README describe what shipped, so they come last. Whole-PR judge. |

`dedupe` may run through waves A to E; it only has to be `merged` before `records`.

The four L2 tasks all edit `src/receipts/verify/rules.py` and `tests/test_verify_claim_numbers.py`, so they are a strict chain (rule: same file, sequential). Splitting (a) to (d) into one task each, or into one task overall, was weighed: one task for all four rules plus their nine tests is well over 300 changed lines; four tasks would give (b) a task of about 40 lines. (a) and (b) are paired because both touch only the claim rule's value sets and neither can move the eleven quote-side counts.

### Semantic coupling across lanes (flagged, handled by the gates)

- `dedupe`'s tests run the real `verify_claim` through `Coordinator`. After `unsigned` lands, the fakes' "9 dollars" and "14 dollars" (`src/receipts/fakes/data.py:15-16`) become checked values (assumption 4 says they keep their outcomes). Every rules task's exit runs `bin/jig`, which runs `tests/test_harness_repair.py`; the `records` judge re-runs it on the merged whole.
- `fuzz_skip.py`, `fuzz_add.py:120` and `fuzz_place_all.py:116` call the private `rules._canonical_number` as their oracle (assumption 13; the `token` verdict's LOW 5). `token` changes that function; its signature (`str -> str`) must not change, and `token`'s exit runs `run_baseline.py`, which runs `fuzz_skip.py`.

### The measurement interface (fixed here, built by `fuzz-port` and `fuzz-claims`)

So that each rules task can be gated on exactly the shapes it closes, `run_baseline.py` takes one optional flag, with the default unchanged from the brief:

- `uv run python scripts/verify_fuzz/run_baseline.py` — all eleven quote-to-page commands plus every claim shape; exit 1 if any fail-open or fail-closed count rises over `expected.txt`.
- `--kinds k1,k2,…` — only those groups. Names: `quote` (the eleven PR #35 commands), and the claim shapes `count`, `unsigned`, `suffix`, `trailing`, `leading_decimal`, `free`, `control`.
- Output: every summary line as the script printed it, then one comparison line per `expected.txt` entry (`<name>: <observed> of <denominator>, expected at most <n> — ok|ROSE`). A fall is printed as `FELL` and does not fail the run; it is reported case by case (assumption 14), and `expected.txt` is not edited to absorb it.
- `expected.txt` holds the brief's baseline table for `quote` (`949741f`'s counts) and, for each claim shape, the post-fix target: WRONG claims verified at most 0 of N and TRUE claims rejected at most 0 of M for every kind except `control`, whose WRONG line is N of N by design (bare non-count integers stay unchecked) and whose TRUE line is 0 of M.

## Scope notes (read before approving)

- **The brief's own file and this plan.** The brief's Allowed list has `docs/superpowers/plans/**` but not `docs/superpowers/briefs/**`. The coordinating session said the brief ships with the PR, as #41's did. The `records` judge is told this one path is an authorized exception to Verification 1, not a scope defect.
- **PR #53 (`jay/readme-redesign`, open, mergeable)** rewrites `README.md` and creates `docs/verifier.md`, moving the verifier rules, the known-limits list and the seven `<details>` examples there (its `README.md:245-266` keeps a short "The verifier" section that says "issue #45 tracks them"; its `docs/verifier.md:27` keeps "Issue #45 tracks all but the last"). This brief edits exactly that README section, and `docs/verifier.md` is not in its Allowed list. Whichever merges second conflicts. **Question 1.**
- **README "Demo: Mel vs Warp" bullets** (`README.md:533-534` on `949741f`; `:461-462` on #53's head): "a known limit tracked in issue #45" and "verified/total can count a repaired claim that duplicates another claim's receipt (issue #45)". After this PR, (h) is an owner-accepted limit and #45 is closed; the duplicate bullet becomes true only across domains (assumption 10). Both lines are outside the brief's README scope ("The verifier" section and one line in "Tests and gates"). **Question 2.**
- PR #49 (`tests/test_ui_render.py`, `tests/test_ui_theme.py`) and PR #54 (`docs/superpowers/plans/**` and briefs, docs only) touch nothing here. #54 adds files under `docs/superpowers/plans/verdicts/`; this plan adds new, differently named files there, so a merge of `origin/main` after #54 lands is clean.

## Limits for every agent (from the coordinating session, 2026-11-18)

No live runs; no paid model or Keenable calls; `scripts/mellea/live_*.py`, `scripts/seed_demo_runs.py` and the app's run endpoint are not run. Never print a secret value. No force-push; merge `origin/main` instead of rebasing. Three repair attempts per failing gate, each fed the exact stderr; on the third failure stop, mark the task `blocked` with the trace, and escalate to the coordinating session ("main"). Wipe `__pycache__` before every measured run. Touch only the paths in your scope. Run `bin/jig` before reporting. Report the jig summary line verbatim.

`UNSET` in the exit commands below is written out in full: `env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE`, because the implementer's shell has several of these from `~/.zshenv` and unit tests must run with none set.

## Human steps

| When | Who | Step |
|---|---|---|
| On approval | owner | Answer the three questions below, or accept the defaults. |
| On approval | orchestrator | Create `.worktrees/gh45` on `jay/gh-45-verifier-follow-ups` from `949741f`; commit the brief and this plan; dispatch `fuzz-port` and `dedupe` together. |
| Before the `records` judge | owner | Merge or hold #53 per question 1, so the integration branch can take `origin/main`. |
| After `records` PASS and both `/verify-claims` PASSes | owner | Open (or approve) the PR `jay/gh-45-verifier-follow-ups` → `main` (`Closes #45`); post the checked #45 comment; merge after the five checks are green. |

## Task graph

```toml plan-graph
[[task]]
id = "fuzz-port"
title = "Commit the six PR #35 fuzz scripts flattened under scripts/verify_fuzz/ (ruff-clean, generating exactly what they generated), plus run_baseline.py and expected.txt for the eleven quote-to-page commands"
scope = [
  "scripts/verify_fuzz/**",
]
deps = []
parallel_safe = true
model = "sonnet"
exit = "find . -name __pycache__ -prune -exec rm -rf {} + && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && uv run python scripts/verify_fuzz/run_baseline.py"
state = "blocked"

[[task]]
id = "dedupe"
title = "(i) A repair that duplicates another claim's receipt is not accepted: pure helper in harness applied before _merge in SpecialistRunner._repair_failing, repaired= counts accepted repairs only; four new tests red first; the existing repair test's setup re-pointed to a different quote; ADR-0007 sentence"
scope = [
  "src/receipts/harness/specialist.py",
  "src/receipts/harness/repair.py",
  "tests/test_harness_repair.py",
  "docs/adr/0007-mellea.md",
]
deps = []
parallel_safe = true
model = "opus"
exit = "find . -name __pycache__ -prune -exec rm -rf {} + && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY uv run pytest -q tests/test_harness_repair.py"
state = "merged"

[[task]]
id = "fuzz-port-repair"
title = "fuzz-port repair 1 of 3 (judge FAIL, verdicts/2026-11-18-gh45-fuzz-port.md; same branch jay/gh-45-fuzz-port): run_baseline.py exits 1 when what the six PR #35 scripts generate changes (pin each script's SHA-256; fail a changed denominator the rules cannot move), so sabotage row 10 turns it red; empty --kinds exits 2; evidence of the red runs and the twelve diff runs in the report"
scope = [
  "scripts/verify_fuzz/**",
]
deps = []
parallel_safe = false
model = "sonnet"
exit = "find . -name __pycache__ -prune -exec rm -rf {} + && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && uv run python scripts/verify_fuzz/run_baseline.py"
state = "merged"

[[task]]
id = "dedupe-docstrings"
title = "dedupe follow-up (judge LOW 1 and 2 accepted, verdicts/2026-11-18-gh45-dedupe.md): the repair.py module docstring (lines 22-24) and the specialist.py module docstring (lines 18-20) state the keeps-own-receipt exception as ADR-0007 line 18 does; docstrings only, no code or test change"
scope = [
  "src/receipts/harness/specialist.py",
  "src/receipts/harness/repair.py",
]
deps = ["dedupe"]
parallel_safe = false
model = "sonnet"
exit = "find . -name __pycache__ -prune -exec rm -rf {} + && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY uv run pytest -q tests/test_harness_repair.py"
state = "merged"

[[task]]
id = "fuzz-claims"
title = "fuzz_claim_values.py (seven kinds, TRUE and WRONG claims per kind on quotes that are on their page), wired into run_baseline.py with --kinds; expected.txt claim-shape lines; red-first run on 949741f rules exits 1 on the claim shapes only"
scope = [
  "scripts/verify_fuzz/**",
]
deps = ["fuzz-port-repair"]
parallel_safe = false
model = "opus"
exit = "find . -name __pycache__ -prune -exec rm -rf {} + && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && uv run python scripts/verify_fuzz/run_baseline.py --kinds quote,control && { uv run python scripts/verify_fuzz/run_baseline.py; test $? -eq 1; }"
state = "merged"

[[task]]
id = "token"
title = "(d) _NUMBER_TOKEN reads $20k, $1.2M, 25$ and $.99 as one token on both sides; _canonical_number expands suffixes and makes $20k = $20,000, $.99 = $0.99, 25$ = $25; test_suffixed_trailing_and_leading_decimal_prices_are_one_number red first"
scope = [
  "src/receipts/verify/rules.py",
  "tests/test_verify.py",
  "tests/test_verify_claim_numbers.py",
]
deps = ["fuzz-claims"]
parallel_safe = false
model = "opus"
exit = "find . -name __pycache__ -prune -exec rm -rf {} + && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && uv run pytest -q tests/test_verify.py && uv run pytest -q tests/test_verify_claim_numbers.py && uv run python scripts/verify_fuzz/run_baseline.py --kinds quote,suffix,trailing,leading_decimal,control"
state = "merged"

[[task]]
id = "unsigned"
title = "(c) '25 dollars', '25 USD', '$ 25', '25 €' read as signed prices in the claim rule only (claim values and the quote's values for that rule, added not substituted); normalize, _match_quote, _occurs_with_whole_numbers, _number_mismatches untouched; three tests, the narrow-rule one green on 949741f"
scope = [
  "src/receipts/verify/rules.py",
  "tests/test_verify.py",
  "tests/test_verify_claim_numbers.py",
]
deps = ["token"]
parallel_safe = false
model = "opus"
exit = "find . -name __pycache__ -prune -exec rm -rf {} + && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && uv run pytest -q tests/test_verify.py && uv run pytest -q tests/test_verify_claim_numbers.py && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY uv run pytest -q tests/test_harness_repair.py && uv run python scripts/verify_fuzz/run_baseline.py --kinds quote,unsigned,suffix,trailing,leading_decimal,control"
state = "merged"

[[task]]
id = "counts-free"
title = "(a) a bare integer followed by a unit from the closed list (credits, seats, users, members, projects, messages, requests, tokens, minutes, hours) is a claim value; (b) a negated or trial 'free' adds no zero price in _quote_values; two tests red first; the three pinned tests pass as written; full run_baseline exits 0"
scope = [
  "src/receipts/verify/rules.py",
  "tests/test_verify_claim_numbers.py",
]
deps = ["unsigned"]
parallel_safe = false
model = "opus"
exit = "find . -name __pycache__ -prune -exec rm -rf {} + && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && uv run pytest -q tests/test_verify_claim_numbers.py && uv run pytest -q tests/test_verify.py && uv run python scripts/verify_fuzz/run_baseline.py"
state = "blocked"

[[task]]
id = "counts-free-repair"
title = "counts-free repair 1 of 3 (judge FAIL, verdicts/2026-11-18-gh45-counts-free.md HIGH 1; same branch jay/gh-45-counts-free): the trial check also covers the plural ('free trials' adds no zero price), a red-first 'free trials' miss case, the rules.py:197 comment and :110-111 docstring sentence match the code, the :652-654 test comment reworded (LOW 5); sabotage row 3 re-run"
scope = [
  "src/receipts/verify/rules.py",
  "tests/test_verify_claim_numbers.py",
]
deps = ["unsigned"]
parallel_safe = false
model = "sonnet"
exit = "find . -name __pycache__ -prune -exec rm -rf {} + && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && uv run pytest -q tests/test_verify_claim_numbers.py && uv run pytest -q tests/test_verify.py && uv run python scripts/verify_fuzz/run_baseline.py"
state = "merged"

[[task]]
id = "records"
title = "rules.py module docstring and the README's 'The verifier' section (number rules, known limits (e) to (h) as owner-accepted with PR #35 rates and denominators, the new assumption limits) plus one 'Tests and gates' line for scripts/verify_fuzz/; README <details> examples re-run; integration branch merges origin/main first; whole-PR judge; PR body and #45 comment drafted for /verify-claims"
scope = [
  "src/receipts/verify/rules.py",
  "tests/test_verify_claim_numbers.py",
  "tests/test_verify.py",
  "README.md",
  "docs/verifier.md",
  "docs/adr/0007-mellea.md",
  "docs/superpowers/plans/**",
  "docs/superpowers/briefs/2026-11-16-gh45-verifier-follow-ups.md",
]
deps = ["counts-free-repair", "dedupe-docstrings"]
parallel_safe = false
model = "opus"
exit = "find . -name __pycache__ -prune -exec rm -rf {} + && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && uv run pytest -q tests/test_verify_claim_numbers.py && uv run pytest -q tests/test_verify.py && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY uv run pytest -q tests/test_harness_repair.py && uv run python scripts/verify_fuzz/run_baseline.py && ! git diff origin/main...HEAD -- src tests scripts | grep -nE '^\\+.*(noqa|type: ignore|pytest\\.mark\\.(skip|xfail)|pyright: (basic|ignore)|per-file-ignores)'"
state = "running"
```

## Per-task dispatch notes and judge gates

Every dispatch carries: the brief, the task's block above, the limits paragraph, and the sentence *"Touch only the paths in your scope. Run `bin/jig` before reporting. Report the jig summary line verbatim."* Every judge gets the brief, `git diff <integration-head>...<task-head>`, the task's block and the gate below, in a fresh context; verdicts go to `docs/superpowers/plans/verdicts/2026-11-18-gh45-<id>.md`. Every judge also runs the brief's Verification 1 forbidden-marker grep on its diff and wipes `__pycache__` before any measured run. **From `641eadd` on, every judge also runs `git diff --exit-code 641eadd -- scripts/verify_fuzz` (the `fuzz-claims` verdict's LOW 3: `fuzz_claim_values.py` is not pinned, so no later task may change what it generates).**

- **`fuzz-port`** — copy the six durable scripts from `/Users/jay/Projects/receipts-drafts/verify_fuzz/` (paths in the brief, "The measurement"), flattened. Make them pass `ruff check` and `ruff format --check` (annotations, complexity at most 6, line length 100) by decomposing, never by changing seeds, `n`, value lists, the order of RNG calls or the printed lines. `run_baseline.py` runs the eleven commands (brief's baseline table), parses the summary lines, compares with `expected.txt`; `expected.txt` names each count's set and denominator. The `--kinds` flag can be added here with `quote` as its only group, or in `fuzz-claims`. **Judge:** Verification 3 in full: each of the eleven commands run twice on the task head (durable copy vs committed copy), outputs diffed without the first `RULES …` line, every diff empty; the committed scripts' summary lines equal the brief's baseline table (on this task the integration head's `rules.py` is `949741f`'s, so that is the same run); sabotage row 10 (change one element of `PRICES` in `fuzz_place_all.py`: the diff and `run_baseline.py` both go red; revert, both green).
- **`dedupe`** — L1. The check is a new pure helper (receipts in, a filtered `Sequence[Claim | None]` out; no I/O) applied to `fixed` before `_merge` (`src/receipts/harness/specialist.py:256-263`, called at `:371`); the INFO line's `repaired=` counts accepted repairs only (assumption 12). Identity per assumption 9 (same receipt kind; `QuoteReceipt` `url`+`quote` exact; `SearchReceipt` `query`+`rank`+`url`; `ts` ignored); order per assumption 11. No import of `receipts.verify.normalize`. `Coordinator` (`coordinator.py`, forbidden), `_TASK` and `judge` in `repair.py` unchanged. `_repair_failing` stays under 60 lines and complexity 6. ADR-0007 gains one statement that a repair duplicating another claim's receipt (within one specialist's claims) is not accepted. The existing test at `tests/test_harness_repair.py:173` changes only its setup (the already-verified claim cites a different quote on `data.SUBJECT_PAGE`). **Judge:** the four new tests red on `949741f` by assertion (copy the test file into a scratch worktree at `949741f`); the changed test's diff touches setup and, as a necessary consequence, only the expected quote of the claim whose setup changed; every other assertion is unchanged (corrected 2026-11-18 on the `dedupe` verdict's LOW 4); sabotage rows 7, 8, 9; `git diff` shows no change to `coordinator.py`, `_TASK` or `judge`; the `DoneEvent` `(1, 2)` and `repaired=0` assertions exist and go red under sabotage row 7.
- **`fuzz-claims`** — **Also, from the `fuzz-port-repair` verdict (findings 1 and 3):** `run_baseline.py` fails (exit 1) when a command's argv (script, seed, `n`, extra arguments) differs from the command named for its entries in `expected.txt`, so lowering a sample size in `run_baseline.py` goes red; `check_pins` fails when any of the six PR #35 scripts has no line in `pinned.sha256` (removing a line or emptying the file goes red); `expected.txt:5` says a `FIXED` denominator change fails. The six scripts and `pinned.sha256` stay byte-identical. The judge sabotages each (lower `n` at the `fuzz_place_all.py` argv; delete one pin line; empty the pin file) and confirms `git diff` leaves the existing argv and pin lines unchanged. `fuzz_claim_values.py` per the brief: for each of the seven kinds, a quote that is on its page (`quote_exact`), a TRUE claim restating the value in an equivalent spelling and a WRONG claim with a different value; prints per kind `WRONG claims verified X of N` and `TRUE claims rejected Y of M`. Deterministic (fixed seed, printed). Wired into `run_baseline.py` and `expected.txt` per "The measurement interface" above. **Judge:** on the task head (still `949741f`'s rules), `run_baseline.py` exits 1 and every `ROSE` line is a claim-shape line; WRONG verified > 0 for each of `count`, `unsigned`, `suffix`, `trailing`, `leading_decimal`, `free`; the eleven `quote` lines all `ok`; for a sample of generated cases, the quote really is a `quote_exact` match on its page (so the measurement exercises the claim rule, not the page rule); `expected.txt` lines name set and denominator; the `fuzz-port` diffs from Verification 3 are still empty (no edit changed what the six scripts generate).
- **`token`** — (d) per brief and assumptions 6 and 7: `_NUMBER_TOKEN` (`rules.py:143`) and `_canonical_number` (`:263-270`) only; `_canonical_number` keeps `str -> str`. `$5 max` and `$5/mo` tokenize as before. Alignment code, `FUZZY_THRESHOLD`, the score window untouched. **Judge:** `test_suffixed_trailing_and_leading_decimal_prices_are_one_number` red on `949741f` by assertion, all four cases; probe 1 (Verification 5) gives the exact note; sabotage row 4 (revert `_NUMBER_TOKEN`) turns the test and the `suffix` and `trailing` shapes red; every one of the eleven `quote` counts is `ok`, and **every** count that moved (either way) is listed case by case with set and denominator, from the `run_baseline.py` output, not a subset of the commands; `git diff` shows `_char_map`, `_aligned_range`, `_fuzzy_miss` and `FUZZY_THRESHOLD` unchanged.
- **`unsigned`** — **From the `token` verdict (MEDIUM 2, LOW 3):** first add the three `_expand_suffix` cases (`$1.2345k` vs `$1,234.5` verifies; vs `$1,234` misses; `$0k` vs `$0` verifies) and show the two sabotages at `rules.py:308` (`or "0"`) and `:310` (digits past the point) go red; pick one spelling for the miss note across (c) and (d) tokens (the brief's assumption 5 names an unsigned price in its signed reading, `$25`; the `token` task writes (d) tokens as written, `25$`) and state the choice in the module docstring. **From the `fuzz-claims` verdict (MEDIUM 1):** the signed reading of an unsigned price must leave no bare integer for a later count reading to pick up (`$ 25 per seat`: the value is `$25`, and `25` is not also a candidate count). Document the order of readings in `_claim_values`'s docstring so `counts-free` can rely on it. (c) per brief and assumptions 3, 4 and 5: the reading feeds `_claim_values` and the claim rule's use of `_quote_values` only, added to (not replacing) the quote's tokens; the miss note shows `$25`. **Judge:** `test_unsigned_prices_in_the_claim_are_checked` and `test_unsigned_price_matches_its_signed_spelling_in_the_claim_rule` red on `949741f` by assertion, `test_unsigned_quote_price_still_misses_a_signed_page_price` green on `949741f` and on the head; probes 2, 3 and 6; sabotage rows 5 (drop the reading from the quote's values: the both-"25 dollars" case and `test_failing_claim_is_repaired_with_the_verifier_reason_then_verified` go red; if the latter does not, report whether `dedupe` had merged into this task's base, since that test lives in L1) and 6 (route the reading into `_match_quote`: the narrow-rule test goes red); `git diff` shows `normalize`, `_match_quote`, `_occurs_with_whole_numbers` and `_number_mismatches` unchanged; the `quote` counts are byte-identical to `token`'s.
- **`counts-free`** — **From the `unsigned` verdict (MEDIUM 1, LOW 2):** add two assumption-4 cases ("Pro costs 25.0 a month." against "Pro costs 25 dollars a month" verifies; "Pro includes 2,500 seats." against "Pro is 2,500 dollars" verifies) and show that substituting the signed readings for the quote's tokens (`_quote_values`, the `tokens = …` line) turns them red; make the `_claim_values` docstring sentence about rule (a) true. **From the `fuzz-claims` verdict (MEDIUM 1, LOW 5):** a required guard test: "Pro costs $ 25 per seat." and "Pro costs USD 25 per seat." against the quote "Pro costs $25 per seat" verify, and "Pro costs $ 30 per seat." misses with `claim numbers not in quote: $30`; a number already read as an unsigned price is not also a count. The "free" test covers `non` ("Starter is a non-free plan" against `$0` misses). (a) per assumptions 1, 2 and 5; (b) per assumption 8. `test_bare_integers_in_the_claim_are_not_checked`, `test_zero_price_in_the_claim_is_matched_by_free_in_the_quote` and `test_free_in_the_quote_covers_only_a_zero_price` are not edited. **Judge:** the two new tests red on `949741f` by assertion; probes 4 and 5; sabotage rows 1 (remove `credits`: the counts test and the `count` shape red), 2 (drop negation) and 3 (drop "free trial": the trial case red); `git diff` touches no line of the three pinned tests; full `run_baseline.py` exits 0 with every line `ok` or `FELL`, each `FELL` listed.
- **`records`** — **From the `counts-free-repair` verdict (LOW 1, 2):** `tests/test_verify_claim_numbers.py` is in scope for the one section comment at `:769` only (say "`trial` or `trials`"), no test or assertion change; the PR description names `test_negated_or_trial_free_does_not_cover_a_zero_price[trials-plural-first-word]` and `[trials-plural-mid-quote]` as red on `ad4cf98` at `:828` by assertion. **From the `counts-free` verdict (LOW 2, 3, 4):** the limits list records, as fail-open under (b), a trial "free" not directly before `trial` ("free 14-day trial", "free: trial"); as fail-closed under (a), a bare number read as a count when a unit follows ("25 per seat" with no sign, "In 2025 users", "GPT-4 tokens"); as fail-closed under (b), a negation counted across punctuation ("No ads, free forever"). The orchestrator flags the "free 14-day trial" gap to "main" for an owner ruling. **From the `unsigned` verdict (LOW 3, 4):** the limits text on the merged head no longer says unsigned prices in the claim are unchecked; the PR description carries the `unsigned` red run (37 failed of 224 on `95e1678`: `test_verify_claim_numbers.py:545` ×19, `:546` ×2, `:581` ×8, `:635` ×2, `:420` ×6). **From the `token` verdict:** the limits list records the mid-word-suffix edge in both directions (a quote cut at `$5m` from a page's `$5mo` is `quote_exact`; the true claim `$5` is then rejected and the wrong claim `$5,000,000` verifies), unless the owner rules on a fix first; the PR description lists the 45 of 160,000 `fuzz_place2.py` quotes that moved `quote_fuzzy` → miss under (d), per seed, from the verdict; the docstring adds "unless a number follows the sign" (`5$20` is `5` and `$20`). The Verification 1 grep and this task's exit are narrowed to `-- src tests scripts` because docs quote the pattern (LOW 6). **Update 2026-11-18 (coordinating session): PR #53 merged into `main` as `3b2673c` at 06:55:30 UTC.** On `3b2673c` the rules, limits list and examples are in `docs/verifier.md` (limits intro at `docs/verifier.md:27`, "Issue #45 tracks all but the last"); the README keeps a short "The verifier" section (`README.md:245-267`) whose sentence at `:265-267` reads "…`$20k` in a claim is read as `$20`. Issue #45 tracks all the limits but one, which is by design."; the Demo bullets are at `README.md:462-463`. **A public LinkedIn post relies on "the README lists the known gaps, such as `$20k` being read as `$20`".** So `records` must: keep the README naming its known limits (never delete that mention silently); replace the `$20k` example with a limit that is still true after this PR (for example plan labels, or values swapped inside one quote, with its PR #35 rate and denominator) and say in the same place that `$20k`-style prices are now read as one number (issue #45); drop "Issue #45 tracks…" in favour of the owner-accepted wording; and the orchestrator flags to "main", before the PR is opened, that the post's `$20k` example stops being true when this PR merges, quoting the old and new README sentences. **Note, 2026-11-19 (coordinating session):** the `$20k` flag is no longer needed. The LinkedIn post has not been posted; as of 2026-11-19 17:19 UTC it reads "(the README lists the known gaps)" with no `$20k` example, and that wording passed a claims check (`docs/superpowers/plans/verdicts/2026-11-19-linkedin-gaps-claims.md`, main checkout). The binding rule stays: the merged README must still name known limits and link `docs/verifier.md`. **The whole-PR judge checks that on the merged head.** first merge `origin/main` into the integration branch (plain merge), re-run the exit. **PR #53 must be on `origin/main` by then (owner, answer 1); if it is not when `records` is ready, the orchestrator tells "main" and waits.** After that merge the verifier rules, limits list and `<details>` examples live in `docs/verifier.md`, and the README keeps #53's short "The verifier" section; the line numbers below are `949741f`'s and are re-located on the merged head. The two "Demo: Mel vs Warp" bullets (`README.md:533-534` on `949741f`) are rewritten: (h) as an owner-accepted limit, duplicates as a cross-domain-only limit (assumption 10), neither citing #45 as open (owner, answer 2). Then the `rules.py` module docstring (`rules.py:1-103`) and the README's "The verifier" section (`README.md:207-339` on `949741f`) describe the same rules; the known-limits list (`README.md:231-242`) names (e) to (h) as accepted by the owner on 2026-11-18 with their PR #35 rates and denominators (for example 22 of 160,000 generated wrong-slot quotes, and the 109,249 wrong-price subset only with its provenance from `count_sets.py`, which is not committed) and the new limits from assumptions 2, 3, 6, 9 and 10; nothing says "scripts in the review records, not in the repository" or lists (a) to (d) or (i) as open; one line in "Tests and gates" says how to run `scripts/verify_fuzz/run_baseline.py`. Each `<details>` example is re-run on the head and its printed output pasted as printed. Drafts of the PR description (`Closes #45`; every red-first run on `949741f` with test name, command, exit code and failing line; all eleven summary lines and every claim-shape line with set and denominator; every skipped test named) and of the #45 comment (shipped rules, rates, the quote-side `$20k` finding) go to the orchestrator's scratch directory, not the repo. **Judge (the PR's `/judge`):** the brief's Verification 1 to 7 in full on `git diff origin/main...HEAD`, the brief file treated as the one authorized path outside Allowed; all six probes; all ten sabotage rows re-run on the merged whole. Then `/verify-claims` (`claims-judge`, fresh context) on each draft with the run outputs as evidence; a FAIL fixes the draft. Verdicts: `verdicts/2026-11-18-gh45-records-whole-pr.md`, `…-pr-body-claims.md`, `…-issue-comment-claims.md`.

## Approval and answers (owner, 2026-11-18 06:16:22 UTC, relayed by the coordinating session, Claude Code session `477932e0`)

1. **Option B: PR #53 merges first.** `docs/verifier.md` is added to the brief's Allowed list and to `records`' scope. Before the `records` judge the integration branch merges `origin/main`, which will then contain #53; if #53 has not merged when `records` is ready, tell "main" and wait.
2. **Yes:** the two README "Demo: Mel vs Warp" #45 bullets are added to `records`' scope (and the brief's Allowed list), rewritten as an owner-accepted limit and a cross-domain-only limit.
3. **Delegated, as for #41:** on each task's judge PASS the orchestrator merges the task branch into `jay/gh-45-verifier-follow-ups`. Never into `main`, never a rebase or force-push. The PR to `main` needs the whole-PR judge PASS and green CI; the main session merges it.

The brief was amended the same minute to match (its "File scope", "Amended 2026-11-18 06:16 UTC" note), which also lists the brief's own path, so the scope note on that path above is resolved. Reports go to "main" at the end of each wave and on any escalation.

## Owner answers before `records` (2026-11-19 17:55:47 UTC, Claude Code session `477932e0`, relayed by the coordinating session)

1. **README wording: "Yes, as planned".** The README keeps naming its known limits; a still-true example with its PR #35 rate and denominator (plan labels, for instance) replaces `$20k`; the same place says `$20k`-style prices are now read as one number; "Issue #45 tracks" is dropped. The LinkedIn post was changed at 17:19:12 UTC to "(the README lists the known gaps)", so the only constraint left is that the README still lists known gaps. The old and new sentences need not be sent first.
2. **The `$5m`/`$5mo` cut-mid-word edge: "Document it as a limit"**, both directions, with an example, in `rules.py`'s docstring, `docs/verifier.md` and the README's limits mention as fits.
3. **"Free 14-day trial": "Document it as a limit".** Assumption 8's rule stays.

Then `records` runs as planned: `origin/main` (`3b2673c`) merged first; the whole-PR judge; `/verify-claims` on the PR body and the #45 comment, which goes to "main" for posting. The PR is not opened and nothing is pushed to `main` by the orchestrator; the report to "main" names the integration head, the PR body draft path and the comment draft path.

## Questions for the owner (answered above; kept for the record)

1. **PR #53 and the verifier text.** #53 moves the README's verifier rules, limits list and examples to `docs/verifier.md`, which this brief does not allow. Default **(A)**: #45 lands first; #53 then merges `origin/main` and moves the updated text, and its "issue #45 tracks them" lines are dropped in that merge. **(B)**: #53 lands first, and `records`' scope adds `docs/verifier.md` (the same edits, in the section's new home) and the brief's Allowed list is amended to match. Which?
2. **The two README "Demo: Mel vs Warp" bullets** (`README.md:533-534`) will cite a closed issue, and the duplicates bullet will overstate the gap (only cross-domain duplicates remain). Default: add those two lines to `records`' scope, rewritten as an owner-accepted limit and a cross-domain-only limit. Alternative: leave them and note the staleness in the PR. Which?
3. **Intra-branch task merges.** For #41 the owner delegated merging each task branch into the integration branch after its judge PASS. That is not pre-approved for #45. Delegate it again (the orchestrator merges, never into `main`, never force-pushes), or does each of the seven PASSes wait for the owner?

## Dispatch log

| Time (UTC) | Event |
|---|---|
| 2026-11-18 06:17 | Integration branch `jay/gh-45-verifier-follow-ups` created at `.worktrees/gh45` from `origin/main` `949741f`; brief and plan committed as `4b2e79a`. `origin/main` re-read at 06:16:48: still `949741f`; PR #53 open. |
| 2026-11-18 06:18 | `fuzz-port` → `running`: worktree `.worktrees/gh45-fuzz-port`, branch `jay/gh-45-fuzz-port` from `4b2e79a`, implementer on `sonnet`. |
| 2026-11-18 06:18 | `dedupe` → `running`: worktree `.worktrees/gh45-dedupe`, branch `jay/gh-45-dedupe` from `4b2e79a`, implementer on `opus`. |
| 2026-11-18 06:25 | `fuzz-port` → `judging`: head `a9d2b82` on `jay/gh-45-fuzz-port`. Exit command re-run by the orchestrator: `bin/jig` format, lint, types, tests all `ok`; `run_baseline.py` exit 0, 20 of 20 comparison lines `ok`, 0 `ROSE`, 0 `FELL`. Implementer note: a `PRICES` value rename (sabotage row 10) changes the durable-vs-committed diff but not `run_baseline.py`'s counts; the judge checks row 10 itself. |
| 2026-11-18 06:33 | `dedupe` → `judging`: head `a38a187` on `jay/gh-45-dedupe`. Exit command re-run by the orchestrator: `bin/jig` exit 0 (format, lint, types, tests `ok`); `tests/test_harness_repair.py` 18 passed, exit 0. Two implementer interpretations put to the judge: (1) the existing test's first assertion list changes its first element `GOOD_QUOTE` → `MONTHLY_QUOTE`, a consequence of the setup change; (2) a repair that keeps its own receipt is accepted even when another agent-written claim cites the same receipt (assumption 11 read literally). |
| 2026-11-18 06:45 | `fuzz-port` → `blocked`: judge FAIL, `docs/superpowers/plans/verdicts/2026-11-18-gh45-fuzz-port.md` (HIGH 1: `run_baseline.py` exit 0 on two `PRICES` changes in `fuzz_place_all.py`, one shrinking the sample from 5,998 to 5,984; MEDIUM 2: no recorded red run; LOW 3: `--kinds ,` exits 0). Items 1 to 5 and 7 passed, including all 12 durable-vs-committed diffs empty. Re-planned as `fuzz-port-repair` (repair 1 of 3), `running` on the same branch and worktree; `fuzz-claims` now depends on it. |
| 2026-11-18 06:55 | `fuzz-port-repair` → `judging`: head `ef30bfd` (adds `scripts/verify_fuzz/pinned.sha256`, changes `run_baseline.py`; the six scripts and `expected.txt` untouched). Orchestrator re-run: `shasum -a 256 -c pinned.sha256` 6 of 6 OK; `bin/jig` exit 0; `run_baseline.py` exit 0, 20 of 20 `ok`. Judged on the whole branch `4b2e79a...ef30bfd`. |
| 2026-11-18 07:05 | `dedupe` → `merged`: judge PASS, `docs/superpowers/plans/verdicts/2026-11-18-gh45-dedupe.md` (0 HIGH, 0 MEDIUM, 4 LOW). Merged into the integration branch as `6dc259c` (plain merge, `a38a187`); `bin/jig` on `6dc259c` exit 0. LOW 1 and 2 (docstrings omit the keeps-own-receipt exception) → new task `dedupe-docstrings`; LOW 3 (the `:186` change and the red runs) → carried into the PR description by `records`; LOW 4 (this plan's gate wording) → corrected in the `dedupe` note. |
| 2026-11-18 07:06 | `dedupe-docstrings` → `running`: worktree `.worktrees/gh45-dedupe-docstrings`, branch `jay/gh-45-dedupe-docstrings` from `6dc259c`, implementer on `sonnet`. `records` now depends on it instead of `dedupe`. |
| 2026-11-18 07:12 | `dedupe-docstrings` → `judging`: head `62370e0` (2 files, 9 insertions, 5 deletions). Implementer: jig attempt 1 failed (line length), attempt 2 green. Orchestrator re-run: `bin/jig` exit 0; `tests/test_harness_repair.py` 18 passed, exit 0. |
| 2026-11-18 07:25 | `fuzz-port-repair` → `merged`: judge PASS, `docs/superpowers/plans/verdicts/2026-11-18-gh45-fuzz-port-repair.md` (0 HIGH, 2 MEDIUM, 1 LOW). Merged into the integration branch as `3e12fc2` (plain merge of `jay/gh-45-fuzz-port` at `ef30bfd`); on `3e12fc2` `bin/jig` exit 0 and `run_baseline.py` exit 0, 20 of 20 `ok`. MEDIUM 2 (evidence) closed from the implementer's report: sabotage `fuzz_place_all.py:34` and `:51` each exit 1 `PIN MISMATCH`, reverts exit 0; scratch `ROSE` exit 1; scratch fixed denominator exit 1; `--kinds ,` exit 2; 12 of 12 durable-vs-committed diffs exit 0. MEDIUM 1 and LOW 3 carried into `fuzz-claims` (dispatch note and gate). `fuzz-claims` is ready. |
| 2026-11-18 07:40 | `dedupe-docstrings` → `merged`: judge PASS, `docs/superpowers/plans/verdicts/2026-11-18-gh45-dedupe-docstrings.md` (1 LOW, accepted without action: rule and exception are adjacent sentences, as ADR-0007 line 18). Merged as `040b8b7`. On `040b8b7`: `bin/jig` exit 0; `run_baseline.py` exit 0, 20 of 20 `ok`; `pytest -q -m "not integration" -rs` with the seven variables unset: 692 passed, 14 deselected (marker `integration`), 0 skipped, exit 0. |
| 2026-11-18 07:41 | **Wave A complete** (`fuzz-port` blocked → `fuzz-port-repair` merged; `dedupe` merged; `dedupe-docstrings` merged). Coordinator news recorded in the `records` note: PR #53 merged as `3b2673c`; the README `$20k` sentence and the LinkedIn post. Nothing running. Next: `bin/plan-check <this file> --ready` → `fuzz-claims`. Orchestrator hands back to "main" for the end-of-wave report. |
| 2026-11-18 07:50 | Resumed on the coordinating session's instruction ("main" is reachable; `records` waits for "main" to confirm the README wording for the LinkedIn sentence). `fuzz-claims` → `running`: worktree `.worktrees/gh45-fuzz-claims`, branch `jay/gh-45-fuzz-claims` from `856e371`, implementer on `opus`. |
| 2026-11-18 08:20 | `fuzz-claims` → `judging`: head `1ab8605` (3 files: `expected.txt`, new `fuzz_claim_values.py`, `run_baseline.py`; six scripts and `pinned.sha256` unchanged, `git diff --quiet` exit 0). Orchestrator re-run: `bin/jig` exit 0; `--kinds quote,control` exit 0; full run exit 1 with 10 `ROSE` lines, 10 of 10 claim-shape. Red-first (seed 45, n = 300 per kind): WRONG verified count 300, unsigned 300, suffix 300, trailing 300, leading_decimal 300, free 147, control 300 (by design), each of 300; TRUE rejected unsigned 104, suffix 138, trailing 82, leading_decimal 55, others 0, each of 300. Implementer risk note for `unsigned`/`counts-free`: read literally, assumption 1 could make `$ 25 per seat` a 25-seat count ("per" as the one word between); the generator avoids unit words in price-claim tails, so this interaction is unmeasured. |
| 2026-11-18 09:05 | `fuzz-claims` → `merged`: judge PASS, `docs/superpowers/plans/verdicts/2026-11-18-gh45-fuzz-claims.md` (0 HIGH, 2 MEDIUM, 4 LOW). Merged as `641eadd`; on it `bin/jig` exit 0 and `run_baseline.py --kinds quote,control` exit 0 (the full run exits 1 by design until the rules land). MEDIUM 2 closed from the implementer's report (recorded on the verdict). MEDIUM 1 → `unsigned` note and a required `counts-free` guard test; LOW 3 → every later judge diffs `scripts/verify_fuzz` against `641eadd`; LOW 5 → `counts-free` "free" test covers `non`; LOW 4 and 6 → `records`. **Wave B complete.** |
| 2026-11-18 09:06 | `token` → `running`: worktree `.worktrees/gh45-token`, branch `jay/gh-45-token` from the integration head after this commit, implementer on `opus`. |
| 2026-11-18 09:40 | `token` → `judging`: head `3135f12` (3 files in scope; `scripts/verify_fuzz` unchanged against `641eadd`). Orchestrator re-run: `bin/jig` exit 0; `test_verify.py` 111 passed; `test_verify_claim_numbers.py` 69 passed; `run_baseline.py --kinds quote,suffix,trailing,leading_decimal,control` exit 0, 28 of 28 `ok`, 0 `ROSE`, 0 `FELL`. Implementer: 25 of 25 new cases red on `fa71ccf` by assertion; the 20 `quote` counts unchanged; underneath, 45 of 160,000 `fuzz_place2.py` quotes moved `quote_fuzzy` → miss (an unlimited counter), every one a `k`/`m`/`b` letter edit landing directly after a page price, listed per seed (11, 11, 15, 8). New fail-closed edge for `records`: quote `$5m` cut from page `$5mo` is `quote_exact` and now rejects the true claim `$5`. |
| 2026-11-18 10:05 | `token` → `merged`: judge PASS, `docs/superpowers/plans/verdicts/2026-11-18-gh45-token.md` (0 HIGH, 2 MEDIUM, 4 LOW). Merged as `bbc2fc3`; on it `bin/jig` exit 0, `run_baseline.py --kinds quote,suffix,trailing,leading_decimal,control` exit 0. MEDIUM 1 (mid-word suffix edge fails both ways) → `records` limit and a flag to "main"; MEDIUM 2 and LOW 3 → `unsigned`; LOW 4 → `records`; LOW 5 → coupling note; LOW 6 → `records` exit narrowed to `-- src tests scripts`. |
| 2026-11-18 10:06 | `unsigned` → `running`: worktree `.worktrees/gh45-unsigned`, branch `jay/gh-45-unsigned` from the integration head after this commit, implementer on `opus`. |
| 2026-11-18 10:40 | `unsigned` → `judging`: head `579a12c` (3 files in scope, 367 insertions, 31 deletions; `scripts/verify_fuzz` unchanged against `641eadd`). Orchestrator re-run: `bin/jig` exit 0; `test_verify.py` 117 passed; `test_verify_claim_numbers.py` 107 passed; `test_harness_repair.py` 18 passed; `run_baseline.py --kinds quote,unsigned,suffix,trailing,leading_decimal,control` exit 0, 30 of 30 `ok`. Implementer: red runs recorded per test, the narrow-rule test green on base and head; the 20 `quote` lines byte-identical to `token`'s; the miss note now names every value in its signed reading (`$25`, `$0.99`), which changes the `token` task's `25$`/`$.99` spelling, for the judge to rule on; reading order: the signed rewrite consumes the number before tokenizing (`$ 25 per seat` → `$25 per seat`), documented in `_claim_values` for `counts-free`. |
| 2026-11-18 11:15 | `unsigned` → `merged`: judge PASS, `docs/superpowers/plans/verdicts/2026-11-18-gh45-unsigned.md` (0 HIGH, 1 MEDIUM, 3 LOW). Merged as `38dcd5d`; on it `bin/jig` exit 0 and `run_baseline.py --kinds quote,unsigned,suffix,trailing,leading_decimal,control` exit 0. MEDIUM 1 (assumption 4 unguarded) and LOW 2 → `counts-free`; LOW 3 and 4 → `records`. The judge ruled the note spelling (`25$` → `$25`, `$.99` → `$0.99`) follows assumption 5 and brief case 4. |
| 2026-11-18 11:16 | `counts-free` → `running`: worktree `.worktrees/gh45-counts-free`, branch `jay/gh-45-counts-free` from the integration head after this commit, implementer on `opus`. |
| 2026-11-18 11:50 | `counts-free` → `judging`: head `ad4cf98` (2 files in scope; test diff is pure additions, 0 removed lines; `scripts/verify_fuzz` unchanged against `641eadd`). Orchestrator re-run: `bin/jig` exit 0; `test_verify_claim_numbers.py` 158 passed; `test_verify.py` 117 passed; **full `run_baseline.py` exit 0, 34 of 34 `ok`, 0 `ROSE`, 0 `FELL`** (the measurement's green run). Implementer: 31 of 31 new red cases by assertion on `b7d70f0`; five sabotages each red then green; the 20 `quote` lines byte-identical to `b7d70f0`'s. Literal-reading edges for the judge and `records`: "Pro costs 25 per seat." (no currency) is a 25 count and fails closed against "$25 per seat"; "free trials", "free 14-day trial", "free: trial" still add zero prices; "free-trial" does not; "No ads, free forever" is read as negated across the comma. |
| 2026-11-18 12:25 | `counts-free` → `blocked`: judge FAIL, `docs/superpowers/plans/verdicts/2026-11-18-gh45-counts-free.md` (1 HIGH: `_TRIAL` is `trial\b`, so "free trials" still adds a zero price and a wrong `$0` verifies, against the brief's Goal; 4 LOW within the brief). Items 1 to 9 met. Re-planned as `counts-free-repair` (repair 1 of 3), `running` on the same branch and worktree; `records` now depends on it. LOW 2, 3, 4 → `records` limits and a flag to "main"; LOW 5 → the repair. |
| 2026-11-18 12:50 | `counts-free-repair` → `judging`: head `021131e` (commits `3b60b79` fix, `021131e` comment; one logic line changed: `_TRIAL` `trial\b` → `trials?\b`; two red-first "free trials" cases). Orchestrator re-run: `bin/jig` exit 0; `test_verify_claim_numbers.py` 160 passed; `test_verify.py` 117 passed; full `run_baseline.py` exit 0, 34 of 34 `ok`. Judged on the whole branch `b7d70f0...021131e`. |
| 2026-11-18 13:20 | `counts-free-repair` → `merged`: judge PASS, `docs/superpowers/plans/verdicts/2026-11-18-gh45-counts-free-repair.md` (0 HIGH, 0 MEDIUM, 2 LOW → `records`; its scope gains `tests/test_verify_claim_numbers.py` for one comment line). Merged as `f6229ab`. **On `f6229ab`: `bin/jig` exit 0; full `run_baseline.py` exit 0, 34 of 34 `ok` (the eleven PR #35 quote counts unchanged from `949741f`; all six claim-shape gaps at 0 of 300 WRONG verified and 0 of 300 TRUE rejected; control 300 of 300 by design); `pytest -q -m "not integration" -rs` with the seven variables unset: 820 passed, 14 deselected (marker `integration`), 0 skipped.** |
| 2026-11-18 13:21 | **Waves C, D, E complete.** All rules (a) to (d) and (i) merged. `records` is the only task left and stays `planned` until "main" confirms the README wording for the LinkedIn sentence (coordinating session, 2026-11-18 ~07:45). `bin/plan-check --ready` lists `records`. Orchestrator reports to "main". |
| 2026-11-19 18:05 | Owner answers recorded (above). `origin/main` re-read: still `3b2673c`. Merged `origin/main` into the integration branch as `e16065f` (plain merge, clean); on it `bin/jig` exit 0 and full `run_baseline.py` exit 0, 34 of 34 `ok`. On `e16065f` the text to rewrite sits at `README.md:264-267` (the `$20k` sentence), `README.md:462-463` (the Demo bullets) and `docs/verifier.md:27` onward (the limits list and `<details>` examples). |
| 2026-11-19 18:06 | `records` → `running`: worktree `.worktrees/gh45-records`, branch `jay/gh-45-records` from the integration head after this commit, implementer on `opus`. Drafts go to the orchestrator's scratch directory, not the repo. |
| 2026-11-19 18:20 | Coordinator update recorded in the `records` note: the `$20k` flag to "main" is no longer needed (the post now reads "(the README lists the known gaps)", claims-checked); the judge gate for `records` gains "the merged README names known limits and links `docs/verifier.md`". |
| 2026-11-19 18:50 | `records` first pass: head `604e54f` (4 files, 259 insertions, 58 deletions). Orchestrator re-run: `bin/jig` exit 0; full `run_baseline.py` 34 of 34 `ok`; marker grep over `src tests scripts` 0 hits; `rules.py` change is docstring-only (implementer AST: 0 of 70 top-level nodes differ, 457 code lines byte-identical); none of the seven `<details>` outputs changed. Drafts written to the scratch directory. The implementer flagged four stale sentences outside its instructions: `README.md:258` (the table row defines a claim value without counts or unsigned prices), `tests/test_verify.py:703` ("tracked in GitHub issue #45"), `tests/test_verify_claim_numbers.py:3-4` ("bare integers are not checked"), `docs/adr/0007-mellea.md:28` (value token in PR #35's terms). Brief Verification 7 requires the record to describe the same rules everywhere, so **`records`' scope is widened to `tests/test_verify.py` and `docs/adr/0007-mellea.md` (both in the brief's Allowed list), prose and comments only**, and a second pass fixes the four lines before the judge. This widening is to complete the record, not to pass a failing gate; the task has not been judged. |
