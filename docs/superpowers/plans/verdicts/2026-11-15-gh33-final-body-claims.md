# Claims verdict: PR #35 final body and issue #45 comment (attempt 3's rules, head `30b6852`)

- **Drafts checked:**
  - `B` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/r3/body-final-a3-filled.md` (115 lines), cited as `B:<line>`. The `{CLAIMS}` placeholder at `B:110` was ignored.
  - `C` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/r3/issue45-final-a3.md` (27 lines), cited as `C:<line>`.
- **Code under the claims:**
  - Branch `jay/gh-33-claim-numbers`, head `30b6852fe306…`. `git ls-remote origin` gives the same commit, and `gh pr view 35 --json headRefOid,baseRefOid` gives `30b6852` / `b526a14` (exit 0).
  - The worktree was not modified. `git status --short` printed 0 lines at the start and at the end.
- **GitHub at check time (2026-11-15 07:42 UTC):**
  - The live PR #35 body is the attempt-5 body (`> **Updated 2026-11-15 (attempt 5, head b0ca3ea)**`), last edited 06:43:31Z (GraphQL `userContentEdits`, exit 0).
  - #45 has 2 comments (03:52:11Z and 06:43:22Z). `updatedAt` is 06:43:22Z. **C is not posted yet.**
- **Method:**
  - `git archive` copies of `30b6852`, `7363a43`, `b8ed8d6`, `b0ca3ea` and `2d0ccbf`, plus two sabotaged copies of `30b6852`.
  - `__pycache__` was removed before every run. Probes ran with `uv run --no-sync python -I` and printed the `rules.py` they imported (`RULES` line).
  - The `30b6852` copy got its own venv (`uv sync --frozen --offline`, exit 0) for `bin/jig` and pytest.

Abbreviations:
- `S` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad`.
- `F` = `S/fv` (this check: copies `F/at-*`, scripts `F/scripts/`, outputs `F/out/`).
- `T` = this session's record, `/Users/jay/.claude/projects/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f.jsonl`.
- `T0` = the coordinating session's record, `/Users/jay/.claude/projects/-Users-jay-Projects-receipts/fb24ba33-869d-4806-aaae-f0de1be3763e.jsonl`.

## Re-run evidence

| Command or artifact | Exit | Result |
|---|---|---|
| `F/at-30b6852`: remove `__pycache__` (2 found), then `./bin/jig` | 0 | format ok, lint ok, types ok, tests ok (`F/out/jig-30b6852.txt`) |
| `uv run --no-sync pytest -q -p no:cacheprovider -m "not integration" -rs` | 0 | 317 passed, 9 deselected, 0 SKIP lines (`F/out/pytest-all-30b6852.txt`). `--collect-only -m integration` lists exactly the 9 named in `B:95`. |
| `tests/test_verify.py` alone, then `tests/test_verify_claim_numbers.py` alone | 0, 0 | 102 passed, 46 passed |
| `python3 -I scripts/leak_gate/check_tracked.py` (worktree at `30b6852`) | 0 | `scanned 123 files against 2 patterns` |
| `F/scripts/ast_cmp.py`: `7363a43`'s `rules.py` against `2d0ccbf`'s and `30b6852`'s | 0 | Full AST differs; AST with docstrings stripped is identical. `git diff 7363a43 30b6852 -- …/rules.py` touches only the module docstring (`rules.py:15-72`). `cmp` of `b8ed8d6` and `b526a14` `rules.py`: identical (exit 0). |
| `git diff --stat origin/main...HEAD`, `git diff --stat b8ed8d6 HEAD`, `git log --format='%H %P'` | 0 | 3 files against `b526a14` (all L2, `AGENTS.md:99`); 11 against `b8ed8d6`. `fa0c84e` has parents `a9ab813` and `b8ed8d6`; `15ee028` has parents `2d0ccbf` and `b526a14`. `2d0ccbf..15ee028` touches only UI files and `docs/assets` PNGs. `15ee028..30b6852` adds one test case (`tests/test_verify.py:735-747`). |
| `F/scripts/probe_final.py` (every example in B and C, 57 cases) on 4 revisions | 0 ×4 | `30b6852` and `7363a43` give identical output (`diff` exit 0). See the claim rows. (`F/out/probe_final.<rev>.txt`) |
| `S/r3/red-final-tests-on-b0ca3ea.txt`, `…-on-b8ed8d6.txt`; `cmp` of their copies | — | The copies hold `30b6852`'s tests and the named `rules.py` (cmp exit 0). The results are 11 failed, 137 passed, exit 1, and 70 failed, 78 passed, exit 1. The 11 names are the 5 + 2 + 3 + 1 that `git diff b0ca3ea 2d0ccbf -- tests/` changes. |
| `S/r3/swa3-out-{1..4}.txt` parsed; `S/r3/sw{1..4}` against `git ls-tree 2d0ccbf` | — | 53 S/R/N/X/A rows, all `SABOTAGED rc=1`; 56 restores, all `rc=0 308 passed, 10 deselected`. Each copy matches `2d0ccbf` (123 files, 0 differ). `S/r3/swj` matches `30b6852` (123 files, 0 differ). |
| `F/scripts/sab_j.py` on copy `F/at-30b6852-J` (J5, J7, J8, the two verify files) | 0 | J5 green (148 passed); J7 red at `[number-split-by-the-page]`; J8 red at `[quote-order-kept]`; restore 148 passed (`F/out/sab_j.30b6852.txt`) |
| **`F/scripts/probe_j5.py` on `30b6852` and on `30b6852` with J5 applied** | 0, 0 | **`mid-page-4`: head `page has 4 there`; J5 `page has no number there`** (`F/out/probe_j5.*.txt`) |
| **`F/scripts/test_j5_pin.py` copied into each copy's `tests/` and run there** | 0, 1 | **Passes on `30b6852`, fails with J5** (`F/out/j5pin.*.txt`). The file was removed afterwards. |
| `F/scripts/classify_closed.py` on the rejected true quotes (`S/r3/cmp-h4/place_all.txt`, `dense9.txt`, `S/judge-r5/out/add5*.tru.7363a43.lst`) | 0 | `place_all`: 195 of 195 have the named number outside the score window. `dense9`: 32 of 35 by the script; the other 3 hold a duplicate price earlier in the window, and by hand their last price lies past the window's end. **`fuzz_add`: 2 of 2 have it inside the window.** (`F/out/classify_closed.30b6852.txt`) |
| `F/scripts/trace_add2.py`, `trace_addmis2.py` | 0, 0 | The 2 add-a-word rejections: the page's own `$9` is inside the window, at 126-128 of (45,136) and 106-108 of (42,115). `Indel.opcodes` ties `on` of `only` and `si` of `single` to `mon`/`basi` past the price, so the quote's `$9` maps to an empty range. The 2 add-a-word wrong prices: the window is on Starter's text and the quote's label `pro` lies outside it (label limit holds). |
| Summary lines of `S/r3/cmp-{main,h4,f4,f5}/*`, `S/cv5/out/spread1.*`, `S/cv5/out/count_sets.txt`, `S/judge-r5/out/add5*.{7363a43,b0ca3ea,1b33a59,b8ed8d6}.txt` | — | Every table cell, see the rows below. 109,249 = 27,430 + 27,332 + 27,175 + 27,312. |
| `git grep` for the three run ids over 40 local and remote-tracking refs (all 20 `ls-remote` heads present at the same SHA) | 0 | `run-0e7ff2b1bb05` only in `tests/test_verify_claim_numbers.py`; `run-4508f95d66ad` nowhere; `run-6a5fe9499c4d` only in `rules.py` and the tests. None is a run record. |
| `T` lines 869, 1801, 2825-2826 (owner answers, option texts) | — | 04:23:00Z "One more repair (Recommended)"; 05:37:16Z "Attempt 5: judge's variant (Recommended)"; 07:10:33Z "Ship attempt 3's rules (Recommended)". The option text: "You accept its round-3 HIGH (about 3% of correct quotes shown as unverified) as a known limit and approve merging without a further judge PASS." |
| `gh api …/pulls/35/comments`, `…/pulls/35/reviews`, `…/issues/35/comments`, `…/issues/33/comments` | 0 ×4 | 0, 0, 1, 0 |
| `S/cv5/scripts/owner_msgs.py` over `T0` and `f1aa1014…jsonl`, 01:12-01:21 UTC | 0 | 3 more texts in each record, all "where are we now?", and 0 answered questions (`F/out/owner_msgs_0112_0121.txt`) |

## Claims verified (no finding)

| # | Claim (summarised) | Evidence |
|---|---|---|
| V1 | `B:1-3`, `C:1`: head `30b6852` ships attempt 3's rules; `rules.py` code is AST-identical to `7363a43`'s with only the docstring changed; round 5 failed | AST and diff rows; `2026-11-15-gh33-r5.md:155` `VERDICT: FAIL` |
| V2 | `B:2`, `B:57-60`: the owner's three choices, the acceptance of round-3 HIGH #1 and the merge without a further judge PASS | `T` lines 869, 1801, 2825-2826 (source citation: finding 6) |
| V3 | `B:4-10`: the live body is attempt 5's (`b0ca3ea`), and its five corrections to the `1823fb9` body are restated | Live body (`F/out/live-pr35-body.md:1-8`); `cl-20-dollars` verifies against a `$25` quote |
| V4 | `B:13`: issue #33, `run-0e7ff2b1bb05`, 24 of 24, the Mel Max example | `gh issue view 33` (exit 0); `issue-mel-max`: main verifies, head `claim numbers not in quote: $180, $200` |
| V5 | `B:15`: neither run record is on any branch; Neon not checked; on `30b6852` the two shapes give `$18` and `$180` | `git grep` row; `live-warp-build`, `live-warp-max` |
| V6 | `B:17-24`: token regex, canonicalisation, `normalize`, out-of-scope words; the exact path, every occurrence tried, the five cut examples | `rules.py:26-38`, `:240-252`; probe `TOKEN_RE`, `exact-*`, `cut-*`, `cl-thousands`, `cl-zero-*`, `cl-05`, `cl-50`, `cl-three`, `cl-1.5k`; `normalize` gives `'save 20% or 20%'` |
| V7 | `B:25-32`: the mechanism; the four miss shapes, each a test; the paired note text | `rules.py:302-353`; probe `fz-billed`, `fz-swapped` (exact note, 97.1), `fz-repeated`, `fz-custom`, `spread-team9`; `tests/test_verify.py:311-313`, `:333-334`, `:513-514`, `:632` |
| V8 | `B:33-34`, `C:3-5`: both label examples verify `quote_fuzzy` on head and on main; a test pins the second | probe `lbl-tier`, `lbl-basic-max-15` on `30b6852` and `b8ed8d6`; `tests/test_verify.py:694`, `:700` |
| V9 | `B:35`, `C:7-10`: 22 of 109,249; 22 of 7,439; 2 of 3,678 add-a-word wrong prices, all label cases | `cmp-h4/place2.*` (1 + 9 + 5 + 7; all 22 are the dropped-price "Pro Max" shape); `cmp-h4/skip{5,6}` (7 + 15); `add5*.7363a43.txt` (1 + 1 + 0); `trace_addmis2` (label outside the window). Set wording: finding 7. |
| V10 | `B:37-38`, `C:12-17`: window at most `len(quote)`; the Business $10 example; tests pin five cases; 195 of 5,998 and 35 of 2,931 are this mechanism | probe `fc-business10` (head: no number there, 90.5; main verifies); `tests/test_verify.py:484-491` (5 ids); `classify_closed` row. The "2 that add a word": finding 2. |
| V11 | `B:40-45`, `C:21`: claim rule, bare integers, `500 credits`, `18000`/`18,000`, unsigned prices on both sides, `free`, swapped values, search receipts out of scope | probe `cl-*`, `cl-q-20-per-month`, `search-out-of-scope` |
| V12 | `B:47-52`: decisions in comment 03:09:20Z from `JayR1031` with the quoted phrase; decision 1's `20 per month` result; decision 2 narrower than #33 | `gh pr view 35 --comments`; probe `cut-currency` (`quote_exact` on `b8ed8d6`, a miss on head) |
| V13 | `B:53-56`: the 01:20 spec and 01:11 ruling in the untracked plan file; neither is an owner ruling; PR 1 comment, 0 reviews, 0 review comments; #33 0 comments | Plan file `:387`, `:393-396`; `git -C /Users/jay/Projects/receipts status --short` shows it `??`; `gh api` rows; owner-message rows (window: finding 14) |
| V14 | `B:61`: `free` came from `run-6a5fe9499c4d` as relayed; not on any branch; effect **pending** | `T0` line 3368 (02:31:58Z); `git grep` row. Meets I4 (re-runnability: finding 9). |
| V15 | `B:63-72`: the five attempts, commits, FAIL verdicts and reasons; the verdicts are untracked in the main checkout | `2026-11-15-gh33.md:89`, `-r2.md:109`, `-r3.md:103`, `-r4.md:131`, `-r5.md:151-152`, each `VERDICT: FAIL`; `git ls-files …/verdicts` = 0 |
| V16 | `B:74-83`: the table's first seven rows, all three columns | `cmp-main`: 2,726, 0, 118, 21,678 (5,373 + 5,466 + 5,438 + 5,401), 6,867, 0; `cmp-h4`: 0, 195, 0, 22, 22, 35; `cmp-f5`: 0, 10, 0, 2, 22, 3; `cv5/out/spread1.*`: 4,239, 0, 1 |
| V17 | `B:84-85`: attempt 3 2 and 2; attempt 5 85 and 333 | `add5*`: `7363a43` 1 + 1 + 0, 0 + 1 + 1; `b0ca3ea` 41 + 29 + 15, 115 + 119 + 99 (main cells: finding 4) |
| V18 | `B:90-96`: head, merges, files, lane, jig, leak gate, 317 / 9 / 0 with the 9 named, 102 and 46 | Re-run rows (base label: finding 10) |
| V19 | `B:102`: 11 failed, 137 passed against `b0ca3ea`, exactly those 11; 70 failed, 78 passed against main | Red-run row |
| V20 | `B:103-105`: 55 of 56 red; 53 of 53 on `2d0ccbf` with every restore at 308; later commits only add a test and merge main; J7 and J8 red on the final files, at baseline 316; the `1 000` test is new | Sweep rows; `S/r3/swa3-J-rerun.txt`; `sab_j` row |
| V21 | `B:108`: no live comparison on `30b6852` | `T` has no `seed_demo_runs.py` run (its one match, line 548, is a file listing). Stated as not measured. |
| V22 | `C:19`, `C:25`: a true claim shows unverified, never the reverse (this mechanism); attempt 5's 85 and 333 | `_fuzzy_miss` returns only misses on this path (`rules.py:371-380`); `add5*.b0ca3ea.txt` |

## Findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| 1 | `B:106`: "**J5 stays green.** Under these rules the score window never reaches a page number after an unmatched last quote number, so a gap reaching the window's end finds nothing." | I1 (false cause, stated as a universal) | HIGH | False. Mid-page, the window is a full `len(quote)` and can end on a page number the quote's unmatched last number does not share a character with. Page "Intro text. Every seat on the Basic plan is billed yearly at 4. More text after it.", quote "Every seat on the Basic plan is billed yearly at 9": window (12,62) ends `'early at 4'`. On `30b6852` the note is `page has 4 there`; with J5 it is `page has no number there` (`F/out/probe_j5.*.txt`, exit 0 each). A note-exact test with that case passes on head (exit 0) and fails with J5 (exit 1) (`F/scripts/test_j5_pin.py`, `F/out/j5pin.*.txt`). J5 is pinnable, which is the fix the round-3 judge asked for (`2026-11-15-gh33-r3.md:104`: "one where the gap reaches the window's end with a page number in it"). | Add that case to `test_numbers_differ_note_exact` (`tests/test_verify.py:749`) and re-run J5. Or drop the sentence and say "J5 is not pinned yet". |
| 2 | `B:37-38`: "When the page text a quote matches is longer, the quote's first or last number can fall outside the window… **Rates:** 195 of 5,998 true quotes; 35 of 2,931…; 2 of 6,941 that add a word." The same text is in `C:12-17` and `rules.py:58-66`. | I3 / I1 (attribution not carried) | HIGH | The 2 add-a-word rejections are not this mechanism. In both, the page's own `$9` lies inside the score window, at 126-128 of (45,136) and 106-108 of (42,115). The alignment ties the added word's letters (`on` of "only", `si` of "single") to page text past the price (`mon`, `basi`), so the quote's `$9` gets an empty range (`F/out/trace_add2.30b6852.txt`). A quote that adds words is shorter than the page text it matches, not longer. The 195 and 35 do fit (`F/out/classify_closed.30b6852.txt`). The misattribution steers the follow-up: widening the window, which C's last section addresses, raised this mechanism to 333 and 450 of 6,941 (finding 3). | Give the 2 their own line: "a word the quote adds next to its price can be aligned past the price inside the window: 2 of 6,941". Fix `rules.py:58-66` the same way. |
| 3 | `C:23`: "Two widened-alignment variants were tried and rejected. **Each fixed limit 2** but let wrong prices verify in other quote shapes" | I4 / I1 (verdict the evidence contradicts) | HIGH | Neither fixed limit 2 (true quotes failing closed). Each lowered it on quotes that leave words out and raised it on quotes that add one:<br>- **Quarter pad (`1b33a59`):** 5 of 5,998 and 3 of 2,931 rejected (`S/r3/cmp-f4/place_all.txt`, `dense9.txt`), but 149 + 153 + 148 = **450 of 6,941** add-a-word true quotes (`S/judge-r5/out/add5*.1b33a59.txt`).<br>- **Slack pad (`b0ca3ea`):** 10 and 3, but **333 of 6,941** (`add5*.b0ca3ea.txt`).<br>- **Attempt 3:** 195, 35 and 2.<br>C's own next line lists the 333. The quarter-pad line also omits that variant's 63 + 52 + 58 = 173 of 3,678 add-a-word wrong prices verified. | "Each lowered limit 2 on quotes that leave words out (195 → 5 and 10 of 5,998; 35 → 3 and 3 of 2,931) but raised it on quotes that add a word (2 → 450 and 333 of 6,941). Each also let wrong prices verify: the quarter pad 107 of 7,439 and 173 of 3,678; the slack pad 85 of 3,678." |
| 4 | `B:84-85`: the `main` column, "not run", for both `fuzz_add.py` rows | I2 / I1 (negative claim, false within its scope) | HIGH | The round-5 judge ran `fuzz_add.py` on `b8ed8d6`. Main verifies 1,091 + 1,048 + 1,539 = **3,678 of 3,678** wrong prices and rejects **0 of 6,941** true quotes (`S/judge-r5/out/add51all.b8ed8d6.txt`, `add52all.b8ed8d6.txt`, `add53one.b8ed8d6.txt`). `2026-11-15-gh33-r5.md:82-84` reports that column. The error hides data that would favour this PR. | Fill the cells with "3,678" and "0". |
| 5 | `C:1`: "**This supersedes the comment of 06:43 UTC**…" | I5 | MEDIUM | The correction is a new reply only. The 06:43:22Z comment still opens "Known limits from PR #35 at branch head `b0ca3ea` (attempt 5…)", with attempt 5's rates (2 of 109,249; 1 of 6,000; 10 of 5,998; 3 of 2,931) and its "To decide" items (`gh issue view 45 --comments`, exit 0). | Edit the 06:43 comment's first line with a dated note: "Superseded 2026-11-15: attempt 5 was not merged; see the comment of <time>". |
| 6 | `B:2`: "The owner then chose "Ship attempt 3's rules"… approved merging without a further judge PASS." `B:57`: "The owner's choices in this session". `C:1`: "the owner chose to ship attempt 3's rules" | I1 (source not named) | MEDIUM | True (`T` lines 869, 1801, 2825-2826; 07:10:33Z for the last). But neither draft names the record or a time, and a PR reader cannot find "this session". This choice is the only authority for merging without the `/judge` PASS that `AGENTS.md:96` requires. | Cite the record and the times (04:23:00Z, 05:37:16Z, 07:10:33Z) and quote the option text. Or ask the owner for a one-line PR comment and cite it. |
| 7 | `B:35`, `C:10`: "2 of 3,678 wrong prices in quotes that add a word"; `B:84` "of 3,678"; `C:25` "85 of 3,678" | Numbers (set and denominator) | MEDIUM | 3,678 is the misquotes that **score ≥ 90** (1,091 + 1,048 + 1,539) out of 10,994 generated (3,683 + 3,611 + 3,700) (`seed=` lines in `S/judge-r5/out/add5*`; `2026-11-15-gh33-r5.md:82-84`). The sets beside it count everything generated: 6,941 true quotes (main verifies 4,002), 5,998 and 7,439. Read side by side, the denominators do not mean the same thing. | "2 of the 3,678 add-a-word misquotes that score ≥ 90 (10,994 generated)". |
| 8 | `B:74-87`, `B:35`, `B:38`, `C:7-17`, `C:24-25`: every random-test rate; `B:103-107`: the 56-row sweep. `B:87` and `C:1` say the scripts are in scratch. | I6 | MEDIUM | Disclosed, still open (the round-1 claims check's finding 10, carried since). Scripts and outputs live under `S/r3/`, `S/judge-r4/scripts/`, `S/judge-r5/` and `S/cv5/`, which a reboot can clear. No row can be re-run from the PR or the issue. | Commit or attach the scripts and outputs (for example under `docs/superpowers/plans/verdicts/gh33-final/`) and cite each by path. |
| 9 | `B:61`: "8 of 19 quote-receipt claims turned unverified, 7 of them correct catches and 1 a false positive." | I6 | MEDIUM | Relayed by the coordinator (`T0` line 3368, 02:31:58Z, a SendMessage). The run record is on none of the 40 refs (`git grep`), and there is no saved query. It is labelled **pending**, which meets I4. | Cite the relay (`T0`, 02:31:58Z). To make it re-runnable, save the query against the run's stored card. |
| 10 | `B:90`: "Base: `origin/main` `b8ed8d6`"; `B:49`: "on `origin/main` (`b8ed8d6`)"; `C:3`: "also true on `main` at `b8ed8d6`" | I1 (revision) | LOW | `origin/main` and the PR's base are `b526a14` (`git ls-remote`; `gh pr view 35 --json baseRefOid`). `rules.py` is byte-identical at both (`cmp` exit 0), so the behaviour claims hold. `B:90`'s "Files changed against `origin/main`: 3" holds only against `b526a14`; against `b8ed8d6` it is 11. | "Base: `origin/main` `b526a14` (`rules.py` unchanged since `b8ed8d6`)". |
| 11 | `B:37`, `C:12`: "It is then a miss, and the note says `page has no number there`" | Precision | LOW | 227 of 230 rejections (195 + 35) say that. 3 name another page price instead: `page has $199 there`, `$200 there` and `$99 there` (`S/r3/cmp-h4/place_all.txt`, `dense9.txt`; the round-3 probe `left-out-then-gap-reads-other`). | "…the note usually says `page has no number there` (227 of 230); otherwise it names a different page price". |
| 12 | `B:97-101`: "Those that still hold stay as they are. Eleven became known-limit tests that pin attempt 3's behaviour: … two spread-case notes name this plan's price." | Precision | LOW | The count of 11 is right (red-run row). But the 2 spread cases pin correct misses, not a known limit. Kept tests were renamed and re-commented: `test_wider_alignment_does_not_pair_a_price_with_another_plans` became `test_quote_price_does_not_skip_the_pages_price_to_the_next_plans`, and `…needs_exactly_one_page_number` became `test_quote_that_left_words_out_meets_this_plans_price_not_the_next_plans` (`git diff b0ca3ea 2d0ccbf -- tests/`). | "Nine became known-limit tests, and two spread-case notes now name this plan's price. The other tests kept their assertions; some were renamed." |
| 13 | `B:103`: "the whole suite with `-m "not integration"`"; `B:104` "308 passed"; `B:105` "at baseline 316" | Numbers | LOW | `S/r3/sabotage_a3.py` also deselects `tests/test_settings.py::test_create_app_boots_with_an_empty_environment`, which spawns `uv run` in a copy with no venv. The 308 is `2d0ccbf`'s 309 minus that test. The 316 is `30b6852`'s 317 minus it. #47 added 7 tests. The body names none of this beside the gate count of 317. | Name the deselected test and why, and give each baseline's set. |
| 14 | `B:56`: "the owner's text messages in the two earlier session records from 00:00 to 01:12 UTC" | I2 (scope) | LOW | The window ends before the 01:20 spec it supports. Re-run for 01:12-01:21: 3 more texts in each record, all "where are we now?", and 0 answered questions (`F/out/owner_msgs_0112_0121.txt`). The conclusion holds. | "00:00 to 01:21 UTC, which hold four texts, each asking where things stand, and no answered question". |
| 15 | `B:15`: "The coordinator reports the same failure on the live voice agent's run `run-4508f95d66ad`" | I1 (source, attribution) | LOW | No record is cited. The record (`T0` line 4126, 03:00:45Z) shows the coordinator's post-deploy check ran `scripts/seed_demo_runs.py --n 1` on Render. The card was fetched from the app's `/api/runs/run-4508f95d66ad` (`T0` line 4211, 03:03:54Z), listing `Warp Build … missing ['$18']` and `Warp Max … missing ['$180']`. That record says nothing about a voice agent. | "the coordinator's post-deploy live run `run-4508f95d66ad` (03:03 UTC, read from the app's `/api/runs`)". |
| 16 | `B:51`: "a claim's `$0`, `$0.00` or "0 dollars" is matched by "free" in the quote" | Clarity | LOW | This restates comment 03:09:20Z correctly. But `rules.py:86` says "`0 dollars` is a bare integer and is not checked". Probe `cl-0-dollars-nofree`: "Starter is 0 dollars." verifies on a quote "Starter is $9 for small teams" (`quote_exact`). | Add "(in the code, "0 dollars" is unchecked: `rules.py:86`)". |
| 17 | `C:1`: "Below are the known limits of the rules that ship" | Completeness | LOW | C lists 3. `rules.py:78-92` also has bare-integer counts, unsigned prices and `free`, which #45's body and its 03:52 comment track. | "Below are the fuzzy-path limits and the swapped-value limit; the others are in this issue's body and the 03:52 comment." |
| 18 | `C:24`: "107 of 7,439 misquotes on word-price pages verified" | Numbers (set) | LOW | The 7,439 are word-price **or different-price** pages, as `C:9` and `B:81` say. | Use `C:9`'s wording. |
| 19 | `B:111`: "- [x] Blind code review: attempt 3 failed round 3…; no further judge PASS, per the owner's decision." | Clarity | LOW | A checked box reads as done or passed. `AGENTS.md:96` requires a `/judge` PASS before merge, and the body does not say that this departs from it. The tests at `30b6852` (the 11 rewritten and the `1 000` case) have had no blind review. | "- [ ] Blind code review PASS: waived by the owner (07:10 UTC), a departure from AGENTS.md section 9; the final tests were not blind-reviewed." |

**Posting condition (from the prior verdicts):** post C to #45 first, confirm it with `gh issue view 45 --comments`, and only then post B. B's "Tracked in #45" (`B:36`, `:39`, `:40`) carries rates that #45 has only once C is posted.

Totals: 0 CRITICAL, 4 HIGH (1-4), 5 MEDIUM (5-9), 10 LOW (10-19).

VERDICT: FAIL

## Round 2 (head `5e37207`, drafts `body-final-a3-v2.md` and `issue45-final-a3.md`)

- **Drafts checked:**
  - `B2` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/r3/body-final-a3-v2.md` (115 lines), cited as `B2:<line>`. `{CLAIMS}` (`B2:110`) is left for the caller.
  - `C2` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/r3/issue45-final-a3.md` (34 lines, rewritten), cited as `C2:<line>`.
- **Code:**
  - Head `5e37207e481c…`, parent `30b6852`. `git ls-remote` and `gh pr view 35 --json headRefOid,baseRefOid` give `5e37207` / `b526a14` (exit 0).
  - `git diff 30b6852 5e37207` changes the `rules.py` docstring (`:58-67`) and adds one case to `test_numbers_differ_note_exact` (`tests/test_verify.py:735-739`, id `gap-reaches-the-window-end`), plus its comment.
  - The worktree was not modified (`git status --short`: 0 lines; HEAD `5e37207`).
- **GitHub at check time:**
  - The 06:43 comment (id 6890515272) has `updated_at` 07:49:21Z and now opens "> **Superseded (2026-11-15 07:49 UTC).** PR #35 does not ship this attempt-5 alignment…". `diff` against `S/c0643-before.md` shows only that note added, plus a trailing newline.
  - #45 has 2 comments, so **C2 is not posted**. The PR body is still the attempt-5 body (`lastEditedAt` 06:43:31Z), so **B2 is not posted**.

### Round 2 re-run evidence

| Command or artifact | Exit | Result |
|---|---|---|
| `F/at-5e37207` (`git archive`, own venv via `uv sync --frozen --offline`, exit 0): remove `__pycache__`, then `./bin/jig` | 0 | format ok, lint ok, types ok, tests ok (`F/out/jig-5e37207.txt`) |
| `uv run --no-sync pytest -q -p no:cacheprovider -m "not integration" -rs` | 0 | 318 passed, 9 deselected, 0 SKIP lines; `--collect-only -m integration` lists 9 |
| The two verify files alone | 0, 0 | 103 passed, 46 passed |
| `python3 -I scripts/leak_gate/check_tracked.py` (worktree at `5e37207`) | 0 | `scanned 123 files against 2 patterns` |
| `F/ast_cmp.py` on `7363a43` and `5e37207` `rules.py` | 0 | Identical with docstrings stripped |
| `git diff --name-only origin/main...5e37207` | 0 | The same 3 files, all L2 |
| `F/scripts/probe_final.py` on `F/at-5e37207` | 0 | Identical to the `30b6852` output (`diff` exit 0) |
| `F/scripts/sab_j.py` on `F/at-5e37207-J` (an exact `5e37207` archive) | 0 | J5 red at `[gap-reaches-the-window-end]`, J7 at `[number-split-by-the-page]`, J8 at `[quote-order-kept]`; baseline and restore 149 passed (`F/out/sab_j.5e37207.txt`) |
| `S/r3/swa3-J-rerun2.txt`; its copy `S/r3/swj` against `git ls-tree 5e37207` | — | Baseline 317 / 10 deselected; J5, J7 and J8 each `rc=1 1 failed`, and each restore is 317. The copy matches in 121 of 123 files. Its `rules.py` is `30b6852`'s (docstring only, AST-identical), and its `tests/test_verify.py` differs from `5e37207`'s in 2 comment lines. The code and test cases match. |
| `S/r3/red-final-tests-on-{b0ca3ea,b8ed8d6}.txt`; their copies | — | 11 failed, 138 passed, exit 1 (the 5 + 3 + 1 known-limit cases and the 2 spread notes); 71 failed, 78 passed, exit 1. The copies' tests match `5e37207`'s and their `rules.py` the named revision (`cmp` exit 0). |
| `pytest --collect-only -m "not integration"` on `F/at-2d0ccbf` | 0 | 309 tests (`B2:105`'s "309 minus that test" holds) |
| Kinds of the 195 `place_all` rejections (`S/r3/cmp-h4/place_all.txt`); `S/judge-r4/scripts/fuzz_place_all.py:82` | — | `drop-word` 102, `drop-price` 76, `punct` 17. The 5,998 true quotes are of 5 kinds: `drop-price`, `typo`, `punct`, `drop-word`, `none`. |
| `T0`, `f1aa1014…jsonl` line 1787 | — | Session `f1aa1014` posted the 03:09 decisions comment, at 03:09:19Z. Session `477932e0` starts at 03:30:22Z. |

### Status of the round-1 findings

| # | Round-1 severity | Status | Evidence |
|---|---|---|---|
| 1 | HIGH | **Fixed** | `B2:102`, `:104-106`. The `…at 4` case pins J5 (sab_j row). 56 of 56 holds. |
| 2 | HIGH | **Fixed** | `B2:38`, `C2:20` and `rules.py:61-66` at `5e37207` give the 2 their own cause, matching `F/out/trace_add2.30b6852.txt`. One wording issue: row R2-4. |
| 3 | HIGH | **Fixed.** A new MEDIUM concerns the table's sets (R2-1). | `C2:26-32`: 195/5/10, 2/450/333 and 173 of 3,678 match `cmp-{h4,f4,f5}/place_all.txt` and `judge-r5/out/add5*` |
| 4 | HIGH | **Fixed** | `B2:84-85`: 3,678 and 0 match `add5*.b8ed8d6.txt` |
| 5 | MEDIUM | **Fixed** | The comment is edited with a dated first line; `C2:1` says so. Posting condition below. |
| 6 | MEDIUM | **Fixed in B2.** One small gap is left in C2 (R2-5). | `B2:2`, `:57-60` cite session `477932e0` and the times, which match `T` lines 869, 1801 and 2826, and quote `AGENTS.md:96`. |
| 7 | MEDIUM | **Fixed** | `B2:35`, `:84`; `C2:14`, `:30-32` |
| 8 | MEDIUM | **Disclosed, still open (I6)** | `B2:87`, `:107`; `C2:5`. Nothing can be re-run from the PR or the issue. |
| 9 | MEDIUM | **Cited, still open (I6)** | `B2:61` cites `fb24ba33` at 02:31:58Z (matches `T0` line 3368). No saved query re-derives 8 of 19, and it is labelled **pending**. |
| 10 | LOW | **Mostly fixed:** `B2:90`, `C2:3`. One place is left (R2-6). | — |
| 11 | LOW | Fixed in B2 and C2. The docstring's wording: R2-4. | `B2:37`, `C2:16` |
| 12 | LOW | Fixed | `B2:97-102` match `git diff b0ca3ea 5e37207 -- tests/` (9 known-limit, 2 note updates, 2 new cases, renames) |
| 13 | LOW | Fixed | `B2:104-106`: 308 = 309 − 1 (collect row), 317 = 318 − 1 |
| 14 | LOW | Fixed | `B2:56`: 00:00-01:21, status questions only, 0 answered (`F/out/owner_msgs_0112_0121.txt`) |
| 15 | LOW | **Fixed.** A small clarity issue is left: R2-7. | `B2:15` matches `T0` lines 4126 and 4211 |
| 16 | LOW | Fixed | `B2:51`, matching `rules.py:86` |
| 17 | LOW | Fixed | `C2:5` |
| 18 | LOW | Fixed | `C2:31` |
| 19 | LOW | Fixed | `B2:111` |

### Round 2 findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| R2-1 | `C2:26`: "Each lowered limit 2 on quotes that leave words out, but raised it on quotes that add a word, **and let more wrong prices verify**", and the table's "Wrong prices verified" column (`C2:30-32`) | Numbers (cells over different sets) | MEDIUM | Each row's cell counts a different set. The shipped row gives only its add-a-word count (2 of 3,678) and leaves out its 22 of 7,439, which the quarter row counts (107). The slack row leaves out its 22 of 7,439 and its 1 of 6,000 (`fuzz_spread`). No row gives `fuzz_place2`, the one shape where **both variants verify fewer** wrong prices than the shipped rules: 2 of 109,249 each against 22 (`S/r3/cmp-f4/place2.*`, `cmp-f5/place2.*`, `cmp-h4/place2.*`). Taken over all four shapes, "more" holds: 46 for the shipped rules, 349 for the quarter pad and 110 for the slack pad. | Give every row the same sets: `fuzz_place2` (22 / 2 / 2 of 109,249), `fuzz_skip` (22 / 107 / 22 of 7,439), `fuzz_spread` (0 / 67 / 1 of 6,000) and `fuzz_add` (2 / 173 / 85 of 3,678). Or say "more in total; fewer on the label shape". |
| R2-2 | `C2:28`: the column header "Leave-words-out quotes rejected (of 5,998)" | Numbers (set) | LOW | The 5,998 are all of `fuzz_place_all`'s true quotes, of 5 kinds (`fuzz_place_all.py:82`). The shipped rules' 195 rejections are 102 drop-word, 76 drop-price and 17 separator-only. `C2:18` calls the same set "true quotes". | "True quotes rejected (`fuzz_place_all`, of 5,998; most leave a word or a price out)". |
| R2-3 | `B2:2`: "in the main Claude Code session (session `477932e0` …)"; `B2:48`: "**Decisions 1 to 4** …: the main Claude Code session made them and recorded them in this PR's comment of … 03:09 UTC" | I1 (attribution) | LOW | The label names two different sessions. The 03:09 comment was posted by session `f1aa1014` (line 1787, 03:09:19Z), which `B2:54-55` call "the coordinating session". Session `477932e0` starts at 03:30:22Z. | Name each session by its id: `B2:48` "the main session at the time (record `f1aa1014`, 03:09:19Z)". |
| R2-4 | `rules.py:61-62` at `5e37207`: "the note usually says `page has no number there` (227 of 230 in the tests below)" | Clarity | LOW | The 230 are random-test rejections (195 + 35), and the docstring names no tests below. In the drafts the same phrase reads "of the 230 rejections below" (`B2:37`, `C2:16`). The body points to the docstring as "the full text" (`B2:17`). | "(227 of the 230 random-test rejections counted next)". This is a docstring change, best done with the next code commit. |
| R2-5 | `C2:3`: "After the round-5 blind verdict failed, the owner chose to ship attempt 3's rules." | I1 (source) | LOW | C2 names no record or time. B2 does (`B2:2`), but C2 is read on its own. | Add "(session `477932e0`, 07:10:33 UTC; see PR #35's body)". |
| R2-6 | `B2:49`: "is `quote_exact` on `origin/main` (`b8ed8d6`)" | I1 (revision) | LOW | `origin/main` is `b526a14` (`git ls-remote`). The result is the same there, because `rules.py` is identical (`cmp` exit 0). | "on `origin/main` (`b526a14`; `rules.py` as at `b8ed8d6`)". |
| R2-7 | `B2:15`: "with the card read from `/api/runs` … Neon, where runs are stored, was not checked" | Clarity (I2 scope) | LOW | Both are true, but they read as a contradiction. The coordinator read the stored card through the app's API (`T0` line 4211, 03:03:54Z); this session queried neither Neon nor the API. | "This session did not query Neon; the coordinator read the card through the app's `/api/runs`." |

**Posting condition:** post C2 first and confirm it with `gh issue view 45 --comments`, then post B2. The edited 06:43 note says "the next comment on this issue gives their known limits and rates", so C2 must be the very next comment on #45. B2's "Tracked in #45" rates (`B2:36`, `:39`, `:40`) exist on #45 only once C2 is up.

Round 2: 0 CRITICAL, 0 HIGH. All four round-1 HIGHs are fixed. 3 MEDIUM are open: R2-1 (new), and round-1 #8 and #9 (disclosed, I6). There are 6 new LOWs.

VERDICT: PASS
