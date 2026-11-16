# Claims verdict: PR #35 body and issue #45 comment, attempt 5 (head `362ce91`)

- **Drafts checked:**
  - `B` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/r3/body-r5-filled.md` (247 lines), cited as `B:<line>`. The `{CLAIMS}` placeholder at `B:242` was ignored.
  - `C` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/r3/issue45-comment-r5-filled.md` (25 lines), cited as `C:<line>`.
- **Code under the claims:** branch `jay/gh-33-claim-numbers`, head `362ce91422811755…` (parent `1b33a59`); `gh pr view 35 --json headRefOid` = `362ce914…` (exit 0); base `origin/main` = `b8ed8d6f…`. The worktree was not modified: `git status --short` printed 0 lines and HEAD was still `362ce91` at the end.
- **Live GitHub state at check time (2026-11-15 ~06:20 UTC):**
  - PR #35 body is the `1823fb9` body (`diff` against `r3/body-before.md` differs only by a trailing newline). The body's edit history has 2 edits, at 02:06:59Z and 03:08:36Z (GraphQL `userContentEdits`, exit 0).
  - PR #35 has 1 issue comment (id 6888366720, `JayR1031`, 03:09:20Z), 0 reviews and 0 review comments (`gh api …/pulls/35/reviews`, `…/pulls/35/comments`, `…/issues/35/comments`, exit 0 each).
  - Issue #33 has 0 comments. Issue #45 has 1 comment and `updatedAt` 2026-11-15T03:52:11Z (`gh issue view 45 --json updatedAt,comments`, exit 0). **Draft C is not posted yet.**
- **Method:**
  - Every probe and fuzzer ran on `git archive` copies of `362ce91`, `1b33a59`, `7363a43` and `b8ed8d6`, with the worktree's venv, `python -I`, `PYTHONDONTWRITEBYTECODE=1`, and `__pycache__` removed first.
  - The `362ce91` copy got its own venv (`uv sync --frozen --offline`, exit 0) for `bin/jig` and pytest.
  - Every probe printed the `rules.py` it imported (`RULES` line).

Abbreviations:
- `V` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/cv5` (this check's copies, scripts in `V/scripts/`, outputs in `V/out/`).
- `R3` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/r3`.
- `RV4` = `docs/superpowers/plans/verdicts/2026-11-15-gh33-r4.md`.

## Re-run evidence

| Command or artifact | Exit | Result |
|---|---|---|
| `V/at-362ce91`: remove `__pycache__` (0 left), then `./bin/jig` | 0 | format ok, lint ok, types ok, tests ok (`V/jig.txt`) |
| `uv run --no-sync pytest -q -p no:cacheprovider -m "not integration" -rs` (`V/at-362ce91`) | 0 | 309 passed, 9 deselected, 0 SKIP lines (`V/pytest-all.txt`). `--collect-only -m integration` lists the 9 named in `B:90`. |
| `tests/test_verify.py` alone, `tests/test_verify_claim_numbers.py` alone, then both | 0, 0, 0 | 101, 46 and 147 passed. Collect-only on `7363a43`: 120. On `1b33a59`: 139. |
| `python3 -I scripts/leak_gate/check_tracked.py` (worktree) | 0 | `scanned 123 files against 2 patterns` |
| `ruff check --no-cache --select C901 --config 'lint.mccabe.max-complexity=0' … rules.py` | 1 (by design) | `_verify_quote` 5. `_char_map`, `_number_mismatches` and `_fuzzy_miss` 4. `pyproject.toml:56` limit 6. AST: the longest function is `_fuzzy_miss`, 32 lines (`rules.py:400-431`). |
| `git diff --name-only origin/main...362ce91`; `git log --format='%H %P'` | 0 | 3 files, all in L2. `fa0c84e` has parents `a9ab813` and `b8ed8d6`. `362ce91` is 1 commit on `1b33a59`. |
| `V/scripts/probe_body5.py`: every example in B and C, on 4 revisions (`V/out/probe_body5.<rev>.txt`) | 0 ×4 | See the claim rows. 53 cases. |
| Final tests on `1b33a59`'s `rules.py` (`V/red`; `cmp` confirms rules = `1b33a59`, tests = `362ce91`) | 1 | 9 failed, 138 passed, the same 9 names as `R3/red-a5-final-tests-on-1b33a59.txt`. The 4 spread cases differ only at the note's index 2. (`V/out/red.txt`) |
| The 9 random-test runs on `V/at-362ce91` (`V/scripts/fuzz5.sh`) | 0 ×9 | With the `RULES` line removed, each output is identical to `R3/cmp-f5/*` (`V/out/fz/`, `V/out/fuzz5.log`) |
| `R3/fuzz_spread.py 1 6000` on 4 revisions | 0 ×4 | `b8ed8d6` 4,239, `7363a43` 0, `1b33a59` 67, `362ce91` 1 (`V/out/spread1.<rev>.txt`). `R3/cmp-*` holds only the `362ce91` output. |
| Scratch copies against the revisions (`cmp`, and `V/scripts/astcmp.py` for AST without docstrings) | 0 | `R3/main`, `h4` and `f4` have `rules.py` byte-identical to `b8ed8d6`, `7363a43` and `1b33a59`. `R3/f5` and `sw1` to `sw4` are AST-identical to `362ce91`. The `sw*` test files are byte-identical to `362ce91`'s. |
| `R3/sweep-final-362ce91.txt` = `cat sw6-out-{1..4}.txt` (`cmp` exit 0), parsed row by row | — | 66 rows, all `SABOTAGED rc=1`. Every id, defect and count equals `B:134-201`. 66 restores, all `rc=0 308 passed, 10 deselected`. 0 lines matching `error`, and **0 exit-code lines**. 4 baselines at 308 / 10. `R3/sw5-out-4.txt`: W8 `rc=0 305 passed` (65 of 66). |
| `V/scripts/sab_lower.py` and `sab_upper.py`: the slack pad ±k, full suite, on copy `V/sab` | 0, 0 | Slack −1, −2, ×¾ and ×½ each turn 1 to 5 tests red. **Slack +2 and +3 each leave 308 of 308 green.** +4 turns `…left_words_out…[euro-each-for-every]` red. The restore is identical. (`V/out/sab_lower.txt`, `V/out/sab_upper.txt`) |
| `V/scripts/trace5.py`, `trace13.py` (slack, widened window, place of each quote number) | 0, 0 | `V/out/trace5.362ce91.txt`, `V/out/trace13.362ce91.txt` |
| `V/scripts/count_sets.py`: replays the fuzzers' RNG without verifying | 0 | `fuzz_place2` seeds 7, 11, 12 and 13: 109,249 of 160,000 quotes hold a wrong slot. `fuzz_spread` seed 1: 1,996 of 6,000 quotes leave no word out (`V/out/count_sets.txt`). `fuzz_skip` by kind (`V/out/skip_kinds.f5.txt`): word price 13 of 2,701, no shared character 8 of 1,645, **shared character 1 of 3,093**. |
| `git grep` for the three run ids over 41 local and remote-tracking refs | 0 | `run-0e7ff2b1bb05` only in `tests/test_verify_claim_numbers.py`, `run-4508f95d66ad` nowhere, and `run-6a5fe9499c4d` only in `rules.py` and the tests. None is a run record. |
| `V/scripts/owner_msgs.py` over the two earlier session records, 00:00 to 01:12 UTC | 0 | 1 text in each record (the same message), "Where are we now." at 01:11:16Z, and 0 answered questions (`V/out/owner_msgs_0000_0112.txt`) |
| `V/scripts/owner_notes.py` over this session's record | 0 | Answers at 04:23:00Z ("One more repair (Recommended)") and 05:37:16Z ("Attempt 5: judge's variant (Recommended)"), with the option texts. Pasted notes at 04:27:07Z (attempt 4: "keep the fix tight", "DO NOT try to solve the pre-existing 1-char plan-label swap", narrow the docstring) and 05:46:57Z (the round-5 checklist). Output: `V/out/owner_notes.txt`. |

## Claims verified (no finding)

| # | Claim (quoted or summarised) | Evidence |
|---|---|---|
| V1 | `B:1`: the owner authorised attempts 4 and 5 after the round-3 and round-4 failures; AGENTS.md allows three; this replaces the `1823fb9` body; the `7363a43` and `1b33a59` drafts were never posted | `V/out/owner_notes.txt` (04:23, 05:37); `AGENTS.md:25`; live body = `1823fb9` body; last body edit 03:08:36Z |
| V2 | `B:3-8`: the five wrong statements in the `1823fb9` body | Each is in the live body (`cv5-pr35-body.md:11`, `:19`, `:34`, `:9`, `:20`) |
| V3 | `B:11`: issue #33, `run-0e7ff2b1bb05`, 24 of 24, the Mel Max example "holds neither price"; main checked only that the quote is on the page | `gh issue view 33` (exit 0); `V/at-b8ed8d6/src/receipts/verify/rules.py:126-140` |
| V4 | `B:13`: neither run record is on any branch; Neon was not checked | `git grep` over 41 refs (above). The scope is stated. |
| V5 | `B:17-23`: token regex, canonicalisation, `normalize`, out-of-scope words; exact path, and the 5 cut examples | `rules.py:164-168`; `probe_body5` `exact-*`, `cut-*`, `cl-zero-*`, `cl-05`, `cl-50`, `cl-three`, `cl-1.5k`; `normalize` gives `'save 20% or 20%'` |
| V6 | `B:24-32`: fuzzy mechanism, slack, exactly-one rule; the 4 misses; the note text | `rules.py:353-397`; `probe_body5` `fz-billed` ($199 there, 95.5), `fz-swapped` (exact note, 97.1), `fz-repeated`, `fz-plus49` ($29, $49 there), `fz-custom`. Each is a miss on `362ce91`, and `b8ed8d6` verifies them all. |
| V7 | `B:33-37`, `C:3-6`: the 3 label-limit examples verify on `362ce91` and on main; `mid-short-tail` is a miss on `7363a43`; the alignment drops "max"; the quote leaves out "free. pro" | `probe_body5` `lbl-*` on all 4 revisions; `V/out/trace5.362ce91.txt` (`delete 'max '`; `insert 'free. pro '`) |
| V8 | `B:41`, `C:14`: the large-elision example is a miss, pinned by a test; `C:15`: the long `pro $9 … lite $1` example | `tests/test_verify.py:712-718`; `probe_body5` `fc-max-200` and `fc-pro9-long` ("page has no number there"; `b8ed8d6` verifies both) |
| V9 | `B:45-50`: claim rule, bare integers, `500 credits`, `18000` / `18,000`, unsigned prices on both sides, `free`, swapped values, search receipts | `probe_body5` `cl-*` and `search-out-of-scope` (a claim with `$999` on a search receipt verifies, `search_log`) |
| V10 | `B:54-58`: decisions in the 03:09 UTC comment from `JayR1031`, "made under the owner's delegation…"; decision 1's `20 per month` result; decision 2 is narrower than #33 | Comment 6888366720; `probe_body5` `cut-currency` (`quote_exact` on `b8ed8d6`, a miss on `362ce91`); issue #33 says "every number token" |
| V11 | `B:59-62`: the coordinator ruling is not an owner ruling; `rules.py` and two test comments say so; the search scope and its result | `rules.py:15-18`; `tests/test_verify.py:219`, `:734`; main-checkout plan file `:387`; the owner-message and GitHub counts above |
| V12 | `B:63-66`: the owner's two choices, the notes after round 3, and the round-5 checklist | `V/out/owner_notes.txt` |
| V13 | `B:67`: the `free` counts are relayed, the run is not on any branch, and the effect is **pending** | `git grep` over 41 refs; stated as pending (meets I4) |
| V14 | `B:69`, `:72`, `:76`, `:77`: RV4 = FAIL with 1 HIGH, 3 MEDIUM and 2 LOW; 107 and 22 of 7,439; the slack pad; 22 on `362ce91` (**the same 22** as `7363a43`: the `OPEN` lines in `R3/cmp-h4/skip{5,6}` and `cmp-f5/skip{5,6}` are identical); the judge's 3 cases plus 3 left-words-out cases are tests; W3, W8, W9 and W10 red; "at most `len(quote)`"; two- to four-price | `RV4:131-140`; `tests/test_verify.py:584-651`; `R3/sweep-final-362ce91.txt` W rows; `rules.py:357-358` |
| V15 | `B:73`: the tie case `busness $290 / $19` verifies; the 3 dense rejections all leave out the word before the last price | `probe_body5` `tie-busness` (verified on `362ce91`, a miss on `1b33a59`); `R3/cmp-f5/dense9.txt` (each omits "for") |
| V16 | `B:75`: W1, W6 and W7 pin the lower bound | Sweep: 11, 7 and 2 red. `sab_lower.py`: slack −1 turns 2 tests red. |
| V17 | `B:85-92`: base, merge, head, files, jig, leak gate, 309 / 9 / 0 with the 9 named, 101 + 46 = 147 (120 at `7363a43`), C901 and length | Re-run evidence table |
| V18 | `B:93-97`: the watched red on `1b33a59`, exit 1, 9 failed and 138 passed, and its breakdown; the file records the command, cwd and `RULES`; W2 reaches the 2 exactly-one cases | `R3/red-a5-final-tests-on-1b33a59.txt` lines 1-2 and the end; re-run `V/out/red.txt`; sweep W2 |
| V19 | `B:99-109`: every cell of the random-test table, and who wrote each script | `R3/cmp-{main,h4,f4,f5}` summary lines. The `362ce91` column was re-run identically. The spread row was re-run on 4 revisions. `RV4:20-22`. |
| V20 | `B:111`: "worse than `7363a43` in two places" | `fuzz_spread` 1 against 0. In the 6 probe outputs in `R3/cmp-{h4,f5}`, only `mid-short-tail` changes to verified. The `place_all`, `dense` and `place2` hits on `362ce91` are subsets of `7363a43`'s (`comm`). |
| V21 | `B:112`: no live run, with scope | Stated as not measured |
| V22 | `B:116-201`: sweep copies, 4 parts, baseline 308 / 10 and why, 66 of 66, restores at 308, no ERROR lines, all 66 rows; earlier run 65 of 66 with W8 green | Sweep parse above; `R3/sabotage_r5.py:191-194` (`--deselect …test_create_app_boots_with_an_empty_environment`); `tests/test_settings.py:81-82` (`uv run --no-sync`) |
| V23 | `B:204-240`: the repair-1 section is kept | `diff` against the live body: only the parenthetical changed, to "(the sweep above; these counts are as of repair 1)" |
| V24 | `C:1-6`, `C:13-19`: two more limits, both in the docstring (`rules.py:60-88`); the examples verify or miss as stated; the rate counts 2 (22), 22 (22), 1 (0), 10 (195) and 3 (35) | `probe_body5`; `R3/cmp-{h4,f5}` |

## Findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| 1 | `B:111`: "every behaviour this body states is a test in the repo." | I1 (false) | HIGH | False. None of these behaviours stated in B is a test: the 3 label-limit examples verifying (`B:35-37`), the left-words-out example (`B:42`), the tie case verifying (`B:73`), a claim's "25 dollars", "25 USD" or "$ 25" verifying against "$20" (`B:47`), and `free` counting in "not free" or another plan's free tier (`B:48`). `grep -n -i -E "Tier A\|Basic \$200 Pro \$1,999\|whole team is \$9 per seat\|lite \$1 a month\|busness\|25 dollars\|25 USD\|\$ 25" tests/*.py`: exit 1. `grep … "not free\|free tier\|free trial\|another plan" tests/test_verify*.py` matches only a comment (`tests/test_verify.py:358`). They reproduce only through `V/scripts/probe_body5.py`. | Drop the sentence, or name what is tested: "the misses and the pinned limit are tests; the label-limit, left-words-out and claim-side limit examples are probes in the review records". Or add the examples as tests. |
| 2 | `B:42`: "when it leaves out words right next to its first or last price ("pro $9, growth $15 a month" on "pro $9 per month, growth $15 a month")." | I1 (stated cause) | HIGH | This pair is a miss on all four revisions, main included, for a different reason: `quote not found on page: best partial_ratio=87.0 < 90` (`V/out/probe_body5.<rev>.txt`, `fc-pro9-short`). The number check never runs. The limit does exist on the longer pair in `C:15`, where `362ce91` gives `page has no number there` (91.4) and main verifies (`fc-pro9-long`). The same short pair is in the committed docstring (`rules.py:84`). | Use C's pair (`…, lite $1 a month` on `…, lite $1 a month.`) in B and in `rules.py:84`. |
| 3 | `C:21`: "All 13 rejections on `362ce91` are the second kind." `B:44`: "all 13 of the second kind." | I1 (attribution not carried) | HIGH | At least 4 of the 10 `place_all` rejections do not fit the second kind as worded ("leaves out words right next to its first or last price"). Each leaves words out after a middle price, one label before the last price: `…starter $200 \| lite $29` (left out "billed monthly"), `…pro $200, lite $8 /yr`, `…starter $15; scale $8` and `…lite $180; pro $19` (`R3/cmp-f5/place_all.txt`). Their mechanism is the first kind's: the last price lies past the widened window. For example, widened `[0,73)` with `$29` at index 76, and widened `[0,59)` with `$19` at 60 (`V/out/trace13.362ce91.txt`). The kind-1 example `fc-max-200` fails the same way (widened `[0,50)`, `$200` at 62). The kinds overlap as worded, so the count of 13 is not a classification anyone can re-run. The same text is in `rules.py:88`. | Classify by mechanism (number past the widened window, or inside it but left unmatched) and give each count, e.g. "N of 13 past the window, M unmatched". Or drop "all 13". Save the classifying script. |
| 4 | `B:74`: "The #45 comment recording the label limit and the fail-closed limit, each with examples and rates, is posted before this round's review." `B:39`, `B:44`: "Tracked in #45." | I1 (false at check time) | MEDIUM | `gh issue view 45 --json updatedAt,comments` (exit 0): 1 comment, `updatedAt` 2026-11-15T03:52:11Z. Draft C is not posted. `rules.py:77` and `:88` at `362ce91` make the same claim. This is RV4 MEDIUM #3 again, unless C goes up first, as the owner's checklist item 1 requires (`V/out/owner_notes.txt`, 05:46:57Z). | Post C, confirm with `gh issue view 45 --comments` that it is there, and only then post B. |
| 5 | `B:45`: "Known limits, tracked in #45:" … `B:49`: "**Swapped values within one quote:** the rule checks that each value is in the quote, not which plan it belongs to." | I1 | MEDIUM | #45 does not track this limit, and C does not add it. #45's body covers bare-integer counts, `free` and the README table. Its 03:52 comment covers unsigned prices. C covers labels and the fail-closed limit (`V/../cv5-issue45.json`; `C:3-21`). `B:82` ("LOW 8 recorded") is true only for the docstring (`rules.py:112-113`). | Add the swapped-values limit to C, or say "recorded in the docstring" for it. |
| 6 | `B:54-58`: "Decisions 1 to 4 … recorded them in this PR's comment of 2026-11-15 03:09 UTC … 3. The equivalences above. 4. The known limits above." | I1 (attribution) | MEDIUM | Comment 6888366720's decision 4 lists two limits: bare-integer counts and `free`. It does not hold the limits B lists "above": labels (`B:33`), fail-closed (`B:40`), unsigned prices (`B:47`) and swapped values (`B:49`). Its decision 3 does not include `1,000` = `1000`, which came from the coordinator's 01:20 spec (main-checkout plan file, "Coordinator spec for L2 repair attempt 2"). Those limits were accepted through the owner's choices and notes (04:23, 04:27 and 05:46 in `V/out/owner_notes.txt`), which `B:63-66` describes separately. | List decisions 3 and 4 as the comment states them. Attribute the label and fail-closed limits to the owner's 04:23 choice and 05:46 checklist, and unsigned prices to the round-2 review and #45's 03:52 comment. |
| 7 | `C:8-11`: "2 of 160,000 quotes on two- to four-price pages (22); 22 of 7,439 on pages with a word price such as "custom" or "free", or a price sharing no character with the quote's (22); 1 of 6,000 quotes that leave words out before a price…". `B:106-109` row labels; `rules.py:72-75`. | Numbers (set and denominator) | MEDIUM | Each set is described other than as the script builds it (`V/out/count_sets.txt`, `V/out/skip_kinds.f5.txt`):<br>- **`fuzz_place2`:** only 109,249 of the 160,000 quotes hold a wrong slot, so the fail-open rate is 2 of 109,249 misquotes.<br>- **`fuzz_skip`:** 3,093 of the 7,439 misquotes are on the "shares a character" kind, which neither B nor C names, and 1 of the 22 hits is of that kind. The by-kind rates are 13 of 2,701 word prices, 8 of 1,645 sharing no character and 1 of 3,093 sharing one.<br>- **`fuzz_spread`:** 1,996 of the 6,000 quotes leave no word out, and every one of the 6,000 is a misquote giving plan 1 plan 2's price, which C does not say. | State each set as built: "2 of 109,249 misquotes (160,000 quotes)"; "22 of 7,439 misquotes whose place has a word price (13 of 2,701), a price sharing no character (8 of 1,645) or one sharing a character (1 of 3,093)"; "1 of 6,000 misquotes that give a plan the next plan's price, 0 to 2 words left out". |
| 8 | `B:33`: "**Known limit, labels are not checked (fails open; also on `main`)**", with `B:37-38` and `B:111` ("Both are recorded under the label limit"); `C:3`, `C:6`, `C:11` | Attribution against the prior verdict | MEDIUM | RV4:131 ruled that a quote keeping its label while the widening pairs its price with the next plan's "is not the pre-existing label problem the owner left out of scope". The two places where `362ce91` is worse than `7363a43` are that class. `mid-short-tail` is a miss on `7363a43` (`probe_body5` `lbl-mid-short-tail`). In the `fuzz_spread` case the quote keeps "scale" and the alignment inserts " $14, max" before `$9` (`V/out/trace5.362ce91.txt`, `spread-ex`). Both exist only because of the widening, and B and C file them under a limit labelled "also on main". The owner's out-of-scope note (04:27) names the "1-char plan-label swap (Tier A vs Tier B)". His 05:46 checklist asks for the "word-price skip rate" to be recorded as its own known limit. | Record these as a separate limit: "the widening can carry a kept label's price to the next plan's when the quote leaves out the page's own price and the next label: 1 of 6,000 in `fuzz_spread`, and `mid-short-tail`; both are misses on `7363a43`". Ask the owner whether the label ruling covers it. |
| 9 | `B:98`: "Attempts 3 and 4's red runs are kept in the review records: 13 failed against `7363a43`, and 11 before that fix was written." | I1, Numbers | MEDIUM | Both runs are attempt 4's, the tests that became `1b33a59` against `7363a43`'s rules. `R3/red-r3-final-tests-on-7363a43.txt` ends `13 failed, 126 passed`, `exit=1`. `R3/red-r3-new-tests-on-7363a43.txt` ends `11 failed, 126 passed`, `exit=1`. Attempt 3's red run is `R3/red-new-tests-on-1823fb9.txt` (`8 failed, 110 passed`). "13 failed" and "11" have no denominator. | "Attempt 4's red runs: 13 failed of 139 against `7363a43`, and 11 of 137 earlier. Attempt 3's: 8 failed of 118 against `1823fb9`." |
| 10 | `B:99`, `B:111`, `B:132`: "The scripts are session scratch files, not in the repo"; `C:1` "scripts in the review records" | I6 | MEDIUM | Neither draft gives a path. The measurements (7 random tests, the 66-row sweep, the probes) live under `/private/tmp/claude-501/…/scratchpad/`, which a reboot can clear. A reader of PR #35 cannot re-run any row. The spread row's `main`, `7363a43` and `1b33a59` cells have no saved output in `R3` (re-run here: `V/out/spread1.<rev>.txt`). This is the round-2 claims check's finding 9, still open. | Commit the scripts and outputs (for example under `docs/superpowers/plans/verdicts/gh33-a5/`), or attach them, and cite each by path. |
| 11 | `B:13`: "On `1b33a59`, both shapes give `claim numbers not in quote: $18` and `…: $180` (round-2 judge probes)." | I1 (revision) | LOW | The head is `362ce91`. It holds there too (`probe_body5` `live-warp-build` and `live-warp-max`, plus `issue-mel-max` → `$180, $200`). | Name `362ce91`. |
| 12 | `B:73`: "The dense test still rejects 3 of 2,931" | Clarity | LOW | The count is the same, but none of the 3 is in `1b33a59`'s 3 (`comm -12`: 0). `1b33a59`'s 3 were ties and now verify. These 3 verify on `1b33a59` and are rejected on `7363a43`. | "Rejects a different 3 of 2,931 (0 in common with `1b33a59`'s)". |
| 13 | `B:75`: "The word-price and left-words-out tests above are the guards a larger pad turns red." `B:72`: "a slack of a few characters stops just short." | Precision | LOW | True for W3, W8, W9, W10 and slack +4 and up. Slack +2 and slack +3 each leave 308 of 308 green (`V/out/sab_upper.txt`). | "…turn red at slack + 4 characters and above; + 2 and + 3 stay green". |
| 14 | `B:121`: "each part's script exited 0." `B:117`: "byte-identical to `362ce91`'s code and tests when copied; `rules.py` differed only in docstring lines" | I1 | LOW | `R3/sweep6.sh` backgrounds the four parts and records no exit status. `R3/sweep-final-362ce91.txt` has 0 exit lines (round-2 claims check finding 12, still open). The second sentence contradicts itself, though the facts hold: AST-identical `rules.py`, byte-identical tests. | Append `echo EXIT=$?` to each part. Say "identical except docstring lines in `rules.py`". |
| 15 | `B:59`: "recorded as "Coordinator rulings" in the W0/W1 plan file." | I1 (reachability) | LOW | The section exists only in the main checkout's untracked copy (`git status`: `?? docs/superpowers/plans/2026-11-14-w0-foundations-and-w1-lanes.md`). `git grep "Coordinator rulings"` over 41 refs finds it in no committed plan file, only `docs/superpowers/briefs/W2-integration.md:3` and `rules.py`. | Say "the uncommitted plan file in the main checkout". |
| 16 | `B:81`: "Round 2 and its body claims check: fixed or recorded (the round-4 verdict's rows)." | I1 | LOW | RV4 has no rows for the round-2 claims check's findings (`RV4:124`: "Not re-checked this round"). That check's findings 9 (scripts in scratch) and 12 (sweep exit code) are still open (findings 10 and 14 here). | Cite the round-3 verdict for round 2, and list the claims-check findings left open. |
| 17 | `C:1`: "The PR body's table also gives the rates for `main`, `7363a43` and `1b33a59`." | I1 (sequencing) | LOW | If C is posted first, as finding 4 needs, the live PR body is still the `1823fb9` body, which has no such table. | Post B right after C, or say "PR #35's body (updated next)". |
| 18 | `C:24`: "check the word before each price. That closes the label gap" | I4 (prediction stated as a result) | LOW | Not measured. It is plausible for the three examples (the word before the price differs: `b:`/`a:`, `max`/`pro`, `is`/`pro`; `V/out/trace5.362ce91.txt`). No random test has been run with it. | "would catch the three examples; not measured on the random tests". |

VERDICT: FAIL

## Round 2 (head `e6835df`, drafts `body-a5b-filled.md` and `issue45-comment-a5b.md`)

- **Drafts checked:**
  - `B2` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/r3/body-a5b-filled.md`, cited as `B2:<line>`. `{CLAIMS}` was ignored.
  - `C2` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/r3/issue45-comment-a5b.md` (29 lines), cited as `C2:<line>`.
- **Code:**
  - Head `e6835dfe94ab…`, parent `362ce91`. `gh pr view 35 --json headRefOid` = `e6835df…` (exit 0), and `origin/jay/gh-33-claim-numbers` points at the same commit.
  - `git diff --stat 362ce91 e6835df` touches only `src/receipts/verify/rules.py` (22 insertions, 18 deletions), all in the docstring. `V/scripts/astcmp.py` on `git show e6835df:…/rules.py` against `362ce91`'s: identical. Both test files are byte-identical to `362ce91`'s.
  - The worktree was not modified (`git status --short`: 0 lines).
- **GitHub at check time:**
  - PR #35's body is still the `1823fb9` body.
  - #45: `updatedAt` 2026-11-15T03:52:11Z, 1 comment (`gh issue view 45 --json updatedAt,comments`, exit 0). **C2 is not posted yet.**
  - `gh pr checks 35` (exit 0): api-image, ci-python, dependency-audit, gitleaks and leak-gate pass. Mermaid is skipping (third party).

### Round 2 re-run evidence

| Command or artifact | Exit | Result |
|---|---|---|
| `V/at-e6835df` (`git archive e6835df`, own venv via `uv sync --frozen --offline`, exit 0): remove `__pycache__`, then `./bin/jig` | 0 | format ok, lint ok, types ok, tests ok (`V/jig-e6835df.txt`) |
| `uv run --no-sync pytest -q -p no:cacheprovider -m "not integration" -rs` | 0 | 309 passed, 9 deselected, 0 SKIP lines (`V/pytest-all-e6835df.txt`). The two verify files alone: 101 and 46 passed (exit 0, 0). |
| C901 at threshold 0 on `rules.py` | 1 (by design) | `_verify_quote` 5. `_char_map`, `_number_mismatches` and `_fuzzy_miss` 4. |
| `python3 -I scripts/leak_gate/check_tracked.py` (worktree at `e6835df`) | 0 | `scanned 123 files against 2 patterns` |
| `V/scripts/probe_body5.py` on `V/at-e6835df` | 0 | The `RULES` line aside, identical to the `362ce91` output (`V/out/probe_body5.e6835df.txt`). `fc-pro9-long`: `page has no number there` (91.4). The label examples and `mid-short-tail` verify. `live-warp-*`: `$18`, `$180`. |
| **W1 on `e6835df` (pad = 0, copy `V/nowiden`), then `fuzz_skip.py 5 6000`, `6 6000` and `fuzz_spread.py 1 6000`** | 0 ×3 | **`fuzz_skip`: 7 + 15 = 22 verified, the same 22 `OPEN` lines as the shipped slack pad** (`diff` exit 0 both seeds, ratio text aside). `fuzz_spread`: 0 (shipped pad: 1). Outputs: `V/out/nowiden.{skip5,skip6,spread1}.txt`. |
| `V/scripts/trace_skip22.py`: 3 of the 22 traced on `e6835df` | 0 | In each, the bare score window already lies on the next plan's text, and the quote's label is aligned to that plan's label: `' for personal projects costs $19 per month.'` (Team→Basic), `'scale for every seat on the team: $199'` (Basic→Scale), `'eams €24 per seat'` (Team→teams). The price sits inside the bare window (`V/out/trace_skip22.e6835df.txt`). |
| `grep -n` in `tests/test_verify.py` for the misses listed in `B2:22-31` | 0 | Each is a test: `:275-281`, `:236-240`, `:311-313`, `:385`, `:569`, `:605`, `:739` |
| Copies `R3/sw1` and `R3/f5` against `e6835df` | — | `rules.py` bytes differ (docstrings); AST without docstrings identical. Tests byte-identical. |

### Status of the round-1 findings

| # | Round-1 severity | Status | Evidence |
|---|---|---|---|
| 1 | HIGH | **Fixed.** One small error remains: row R2-4. | `B2:117`. Every miss listed under Rules is a test (grep row above). The tie case is marked "a probe, not a test" (`B2:78`). |
| 2 | HIGH | **Fixed** | `B2:45`, `C2:19` and `rules.py` (e6835df docstring) use the `… lite $1 a month` pair. On `e6835df` it is a miss (`page has no number there`, 91.4), and `b8ed8d6` verifies it. |
| 3 | HIGH | **Fixed** | "all 13" is gone from `B2`, `C2` and `git show e6835df:src/receipts/verify/rules.py`. The second kind now reads "right next to one of its prices" (`B2:45`, `C2:19`), and no per-kind count is claimed. |
| 4 | MEDIUM | **Open, as a posting condition.** | `B2:79` says the #45 comment "was posted before this body", but #45 still has 1 comment (03:52:11Z). The coordinator's order is to post C2, confirm, then post B2. If that order is kept, the claim is true when B2 goes up. |
| 5 | MEDIUM | **Fixed once C2 is posted** | Item 4 at `C2:23`. The probe `cl-swapped-in-quote` verifies (`quote_exact`). |
| 6 | MEDIUM | **Fixed.** One small error remains: row R2-5. | `B2:60-61` match comment 6888366720's decisions 3 and 4. `B2:63` names the 01:20 coordinator spec for `1,000` = `1000`, which matches the plan file's "Coordinator spec for L2 repair attempt 2". |
| 7 | MEDIUM | **Fixed** | `B2:37`, `:41`, `:112`, `:113`, `:115`; `C2:7`, `:14-15`. These agree with `V/out/count_sets.txt` (109,249; 4,004). Every `fuzz_skip` misquote has a word or a different price at its place (`fuzz_skip.py` builds only those), so the 7,439 description now fits. |
| 8 | MEDIUM | **Fixed for the two widening cases. The fix moved the 22 of 7,439 with them, and that is wrong (R2-1, HIGH).** | `B2:39-42`; `C2:9-15`; `rules.py` (e6835df). |
| 9 | MEDIUM | **Fixed** | `B2:104`: 13 + 126 = 139 and 11 + 126 = 137, matching `R3/red-r3-final-tests-on-7363a43.txt` and `R3/red-r3-new-tests-on-7363a43.txt` |
| 10 | MEDIUM | **Disclosed, still open (I6).** | `B2:117` now says the scripts and outputs cannot be re-run from the PR, and that the three `fuzz_spread` cells were printed and not saved. I re-ran those three and got the same counts. A number that cannot be re-run from the record stays MEDIUM. Fix: commit or attach the scripts and outputs. |
| 11 | LOW | Fixed | `B2:13` names `e6835df`. The probe on `e6835df` gives `$18` and `$180`. |
| 12 | LOW | Fixed | `B2:78` says "a different 3". |
| 13 | LOW | Fixed | `B2` sweep section, "Not pinned". This matches `V/out/sab_upper.txt` (+2 and +3 green, +4 red). |
| 14 | LOW | Exit codes fixed. The copies sentence has a new small error: row R2-6. | `B2` sweep section: "The parts' exit codes were not recorded." |
| 15 | LOW | Fixed. One new forward-looking clause: row R2-7. | `B2:64` names the untracked file |
| 16 | LOW | Mostly fixed: row R2-8 | `B2:86-87` |
| 17 | LOW | Fixed | `C2` no longer cites the PR body |
| 18 | LOW | Fixed | `C2:26` says "targets" |

### Round 2 findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| R2-1 | `B2:39`: "**Known limit, a price carried past the page's own price (fails open):** the widened alignment can carry a quote price past the page's own price at its place … to the next plan's equal price." `B2:41`: "**Rates:** 22 of 7,439 misquotes on pages whose own price at that place is a word or a different price (`7363a43`: 22, `1b33a59`: 107)." Also `C2:9`, `C2:14`, the `e6835df` docstring, and `C2:27` ("For 2: bound the alignment so a quote price cannot pass a page price slot"). | I1 (cause attribution not carried) | HIGH | **The widening does not cause the 22.** With the widening removed from `e6835df` (W1, `pad = 0`), `fuzz_skip` seeds 5 and 6 verify the same 22 misquotes, line for line (`V/out/nowiden.skip{5,6}.txt` against `R3/cmp-f5/skip{5,6}.txt`, `diff` exit 0). `7363a43`, which has no widening, verifies the same 22 too (`R3/cmp-h4` and `cmp-f5` `OPEN` lines identical). In the traced cases, the bare score window is the next plan's text with the quote's label aligned to the other label. That is the label limit as `B2:33` defines it ("a changed … plan name beside a price can attach another plan's real price"), not a price carried past its own slot by the widening (`V/out/trace_skip22.e6835df.txt`). Only `fuzz_spread`'s 1 of 6,000 (0 with `pad = 0`) and `mid-short-tail` (a miss on `7363a43`) depend on the widening. The error steers the follow-up. The fix proposed for item 2 cannot reach the 22, because none of them passes a page price slot. The fix proposed for item 1 ("check the word before each price") would not catch most of them either, because quote and page share that word (`costs $19`, `team: $199`). | Move the 22 of 7,439 back to the label limit, next to the 2 of 109,249. Give the carried-past limit only the widening-dependent rates: 1 of 6,000 (`fuzz_spread`; 0 with no widening and on `7363a43`) and `mid-short-tail`. If 107 is kept as a comparison, state that the quarter pad's extra 85 were the carried-past kind and are gone. Fix the `e6835df` docstring the same way. Recheck `C2:26-27` against the 22. |
| R2-2 | `B2:79`: "A #45 comment … was posted before this body and before this round's review." | I1 (false until posted) | MEDIUM (round-1 #4, open) | `gh issue view 45 --json updatedAt,comments`: 1 comment, 03:52:11Z | Post C2, run `gh issue view 45 --comments` to confirm it shows, then post B2. |
| R2-3 | `B2:117`: "The scripts and outputs live only in this session's scratch directory, so they cannot be re-run from this PR." | I6 | MEDIUM (round-1 #10, disclosed) | The statement is true. The measurements still cannot be re-run from the PR. | Commit or attach the scripts and outputs. |
| R2-4 | `B2:117`: "The known-limit examples are probes, except the large-elision case, which a test pins." | I1 | LOW | The quote-side example of the unsigned-price limit (`B2:50`, "20 per month" on "$20 per month" is a miss) is also a test (`tests/test_verify.py:739`). | "…except the large-elision case and the quote-side `20 per month` case, which tests pin". |
| R2-5 | `B2:63`: "The rest come from the blind reviews' findings on this PR, and each is recorded in `rules.py` and #45." | I1 | LOW | "The rest" includes rules, not just limits. The exact-path edge rule and the slack pad are not in #45, and the number-token regex is from the same 01:20 coordinator spec (plan file), not from a blind review. | "The other limits come from the blind reviews, and each is recorded in `rules.py` and #45. The token regex is also from the 01:20 spec." |
| R2-6 | `B2` sweep section: "Four scratch copies of the tracked files, whose code and tests were byte-identical to `362ce91`'s" | I1 | LOW | The tests are byte-identical. `rules.py` is not: in `R3/sw1`, its bytes differ from both `362ce91`'s and `e6835df`'s (docstrings), and its AST without docstrings is identical. | "tests byte-identical, `rules.py` AST-identical (docstrings aside)". |
| R2-7 | `B2:64`: "the W3 wrap-up commits it" | I1 (future stated as fact) | LOW | No commit or artifact shows this. It is a plan. | "the W3 wrap-up is to commit it". |
| R2-8 | `B2:87`: "Its other findings concerned that draft's wording, which this body replaces." | I1 | LOW | The round-2 claims check's findings 9 (scripts not committed), 10 (the `free` run cannot be re-run) and 12 (sweep exit code) were about evidence, not wording. They recur here, disclosed at `B2:117`, `:72` and the sweep section. | "…its findings on evidence (9, 10, 12) are disclosed above, not fixed". |

Round 2: 1 HIGH (R2-1, new), 2 MEDIUM still open (R2-2, which is a posting condition, and R2-3, disclosed), and 5 LOW. Round 1's three HIGHs are fixed.

VERDICT: FAIL

## Round 3 (head `521cecb`, drafts `body-a5c-filled.md` and `issue45-comment-a5c.md`)

- **Drafts checked:**
  - `B3` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/r3/body-a5c-filled.md`, cited as `B3:<line>`. `{CLAIMS}` was ignored. `diff` against `B2` changes only lines 1, 13, 37, 39, 41, 63-64, 75, 87, 91-92, 105, 107, 117-118, 120, 123 and 251.
  - `C3` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/r3/issue45-comment-a5c.md` (29 lines), cited as `C3:<line>`.
- **Code:**
  - Head `521cecb45f41…`, parent `e6835df`. `gh pr view 35 --json headRefOid` = `521cecb…` (exit 0), and `origin/jay/gh-33-claim-numbers` points at the same commit.
  - `git diff e6835df 521cecb` is 12 insertions and 10 deletions, all in the `rules.py` docstring (`:64-85`). `V/scripts/astcmp.py` on `git show 521cecb:…/rules.py` against `362ce91`'s: identical. `git diff --quiet 362ce91 521cecb -- tests/…` exits 0 for both test files.
  - The worktree was not modified (`git status --short`: 0 lines).
- **GitHub at check time:**
  - PR #35's body is still the `1823fb9` body.
  - #45: `updatedAt` 2026-11-15T03:52:11Z, 1 comment (exit 0). **C3 is not posted yet.**
  - `gh pr checks 35` (exit 0): api-image, ci-python, dependency-audit, gitleaks and leak-gate pass. Mermaid is skipping.

### Round 3 re-run evidence

| Command or artifact | Exit | Result |
|---|---|---|
| `V/at-521cecb` (`git archive 521cecb`, own venv, `uv sync --frozen --offline` exit 0): remove `__pycache__`, then `./bin/jig` | 0 | format ok, lint ok, types ok, tests ok (`V/jig-521cecb.txt`) |
| `uv run --no-sync pytest -q -p no:cacheprovider -m "not integration" -rs` | 0 | 309 passed, 9 deselected, 0 SKIP lines (`V/pytest-all-521cecb.txt`) |
| `python3 -I scripts/leak_gate/check_tracked.py` (worktree at `521cecb`) | 0 | `scanned 123 files against 2 patterns` |
| `V/scripts/probe_body5.py` on `V/at-521cecb` | 0 | The `RULES` line aside, identical to the `362ce91` output (`V/out/probe_body5.521cecb.txt`) |
| `V/scripts/trace_all22.py` over the 22 `OPEN` lines of `R3/cmp-f5/skip{5,6}.txt`, on `521cecb` | 0 | In all 22, the quote's own plan label lies outside the bare score window. **The quote and the page share the word before the price in 21 of 22.** In 21 of 22 the window is on a later plan's text. In 1, it is on an *earlier* plan's: page `Starter … costs $99 per month, Plus … contact sales, Team … costs €14, Growth … costs $99.`, quote `Team … costs $99`, bare window `'ter with unlimited projects and sso costs $99 '`. Outputs: `V/out/trace_all22.521cecb.txt` and `V/out/trace_case20.521cecb.txt`. The script's own plan-segment column is a heuristic and is not relied on; the window text and label positions are. |
| `comm` of the 22 `OPEN` lines against `R3/cmp-main/skip{5,6}.txt` | 0 | 0 of the 22 are missing on main, so main verifies all 22 ("also on `main`" holds). |
| `V/scripts/probe_mst_nowiden.py` on `V/nowiden` (`e6835df` code with `pad = 0`) | 0 | `mid-short-tail` is a miss (`page has no number there`, 91.7), so it depends on the widening (`V/out/mst.nowiden.txt`) |
| Earlier runs this check relies on | — | `V/out/nowiden.skip{5,6}.txt`: the same 22 with `pad = 0`. `V/out/nowiden.spread1.txt`: 0. `V/out/spread1.1b33a59.txt`: 67. `V/out/spread1.7363a43.txt`: 0. |

### Status of the round-2 findings

| # | Round-2 severity | Status | Evidence |
|---|---|---|---|
| R2-1 | HIGH | **Fixed.** One small error remains: row R3-2. | The 22 of 7,439 are now under the label limit, with the `pad = 0` and `7363a43` baselines (`B3:37`, `C3:9`, `rules.py:67-74` at `521cecb`). The carried-past limit keeps 1 of 6,000 (`pad = 0`: 0; `7363a43`: 0; `1b33a59`: 67) and `mid-short-tail` (`B3:39-41`, `C3:11-15`). Both depend on the widening (rows above). `C3:26` now compares the nearest label, and `C3:27` concerns item 2 only. |
| R2-2 | MEDIUM | **Open, as a posting condition** | `B3:79` says the #45 comment "was posted before this body", but #45 still has 1 comment (03:52:11Z). The claim holds only if C3 is posted and confirmed first, as the coordinator states. |
| R2-3 | MEDIUM | **Disclosed, still open (I6)** | `B3:117` |
| R2-4 | LOW | Fixed | `B3:117` names the quote-side "20 per month" case (`tests/test_verify.py:739`) |
| R2-5 | LOW | Fixed | `B3:63`: the regex comes from the 01:20 spec, rules are recorded in `rules.py`, and limits are tracked in #45 |
| R2-6 | LOW | Fixed | `B3:123` matches the `cmp` and AST results for `R3/sw1` |
| R2-7 | LOW | Fixed | `B3:64`: "is planned to commit" |
| R2-8 | LOW | **One small error remains: row R3-3.** | `B3:87` |

### Round 3 findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| R3-1 | `B3:91`: "Head: `521cecb`, three commits on `1b33a59`: `362ce91` (the slack pad and its tests), then `521cecb` and `521cecb` (docstrings only…)" | I1 (revision) | LOW | The second id is wrong. The commits are `362ce91`, `e6835df` and `521cecb` (`git log --format='%h %p %s' -2`; `git rev-list --count 1b33a59..521cecb` = 3). | "then `e6835df` and `521cecb`" |
| R3-2 | `B3:37` (and `rules.py:72-73` at `521cecb`): "the bare score window already sits on the next plan's text, with the quote's label aligned to that plan's." | I1 (precision) | LOW | This holds for 21 of 22. In 1, the window sits on an *earlier* plan's text (Starter's `$99`, before Team; `V/out/trace_case20.521cecb.txt`). `C3:9` is scoped "in each traced case" and is true as written. | "on another plan's text (a later plan's in 21 of 22)". Or scope it to the traced cases, as C3 does. |
| R3-3 | `B3:87`: "its findings 9, 10 and 12 recur here as disclosures (the red runs' records, the scratch-only scripts, the sweep's exit codes)." | I1 | LOW | The round-2 claims check's finding 10 is the relayed `free` run (`2026-11-15-gh33-r2-body-claims.md:41`), not the red runs' records. The red-run record was its finding 7. 9 covers the scratch-only scripts, and 12 the exit codes. | "(the scratch-only scripts, the relayed `free` run, the sweep's exit codes)" |
| R3-4 | `C3:26`: "in many of the 22, quote and page share that word" | Numbers | LOW | 21 of 22 (`V/out/trace_all22.521cecb.txt`). | "in 21 of the 22" |

Round 3: 0 CRITICAL, 0 HIGH. 2 MEDIUM are still open: R2-2, a posting condition, and R2-3, disclosed. There are 4 LOW. Every round-1 and round-2 HIGH is fixed.

**Condition on this PASS:** post C3 to #45 first, and confirm it with `gh issue view 45 --comments`, before posting B3. Otherwise `B3:79`, and "tracked in #45" at `B3:38`, `:42`, `:47` and `:48`, are false when they go up.

VERDICT: PASS
