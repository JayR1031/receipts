> Round 4 claims check by a read-only claims-judge subagent, 2026-11-15 19:11–19:25 UTC. The local clock ran about 1 min behind GitHub's and Render's `Date` headers. Reviewed text:
> - `README.md`, `docs/adr/0004-approved-ai-vendors.md` and `scripts/mellea/*.py` at `97afe57`, the PR #50 head. `git ls-remote` gave `97afe57` at 19:11:46Z and again at 19:24:30Z. The base is `d719360`.
>   - Focus: `git diff ea455ef 97afe57` (3 files, 18 insertions, 10 deletions).
>   - Then every part of the full diff that those changes touch.
> - `/Users/jay/Projects/receipts-drafts/social-posts.md`: sha256 `8c193bf12a710eb7…`, mtime 19:10:48Z, unchanged at the end.
> - The PR #50 description draft `…/scratchpad/w3/pr50-body.md`: 29 lines, mtime 19:11:21Z, unchanged at the end. `{CI}`, `{CLAIMS}` and `{JUDGE}` were not checked.
> - The issue #45 comment draft `…/scratchpad/w3/issue45-suffix-comment.md`: 8 lines, mtime 19:10:48Z.
>   - It is judged as if posted.
>   - #45 still had 4 comments at 19:24Z, so it is not posted yet.
>
> **Privacy:** this file quotes no Codex session id, time, folder or file name. Finding N1 refers to round 3's finding 2 by number only. No GPS value and no secret is printed.

# Claims verdict, round 4: W3 README (PR #50), ADR-0004, Mellea scripts, social posts, PR description, #45 comment

**Base and deploy.**
- `/healthz` at 19:15Z: HTTP 200, `"sha":"d719360"`, `x-receipts-mode: live`.
- `git diff --stat d719360 97afe57 -- src tests pyproject.toml uv.lock bin` is empty (exit 0), so the code under the texts is the deployed code.

**Re-run artifacts.** These are in the scratchpad and are not durable: `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/w3claims-r4/`
- **Copies:** `copy-97afe57/` and `copy-d719360/`, both made with `git archive`.
- **How the Python ran:** `env -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u DATABASE_URL -u DEMO_PASSCODE PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=…/copy-d719360/src …/w3-credits/.venv/bin/python`, from `emptycwd/`.
- **New script:** `scripts/suffix_r4.py` (exit 0).
- **Reused from round 3** (`…/w3claims-r3/scripts/`), all exit 0: `ast_compare.py`, `x_weight.py` and `suffix_rate.py`.
- **`web/`:**
  - `runs.json` and `runs/run-*.json`: 4 GETs, all HTTP 200, at 19:21Z;
  - `landing.html`: HTTP 200 at 19:19Z.
- **`remote-branches.tsv`:** from `gh api repos/JayR1031/receipts/branches` (exit 0).
- **Side effect, scratch only:** the first pytest run's subprocess (`uv run --no-sync`) created an empty venv inside `copy-97afe57`. It was moved to `uv-created-empty-venv/`. The worktree had 0 changed files before and after (`git status --short`).
- **Not done:**
  - no script under `scripts/mellea/` was executed;
  - no POST was sent;
  - no model or Keenable call was made;
  - `~/.codex`, `~/Documents/Codex` and the session transcript were not read.

## Verdict per text

1. **README, ADR-0004 and `scripts/mellea/` (PR #50 at `97afe57`): FAIL.**
   - HIGH finding N1 is in ADR-0004:35.
   - The README on its own has no HIGH. It has MEDIUM finding N2.
   - ADR-0004 also has LOW finding N6, and the scripts have LOW finding N5.
2. **Social posts: PASS.** No findings.
3. **PR #50 description draft: PASS.**
   - It has no HIGH: MEDIUM finding N3 and LOW finding N7.
   - :14 ("`bin/jig` exit 0 at `97afe57`") must be refreshed if N1's fix lands as a new commit.
4. **Issue #45 comment: PASS.** It has no HIGH: MEDIUM finding N4.

## Round 3 findings: status at `97afe57` and in the drafts

| R3 # | Status | Evidence |
|---|---|---|
| 1 HIGH "$-price" | **Fixed** | **LinkedIn:** posts:20 says "It checks each $-price in a quoted claim against that quote (the README lists the known gaps, such as $20k being read as $20)".<br>**X 2/:** posts:74 says "Now a quoted claim's $-prices are checked against its quote."<br>**`suffix_r4.py` (exit 0):**<br>• Controls: K0 (claim `$25`, quote `$20`) is not verified ("claim numbers not in quote: $25"), and K1 (`$20` against `$20`) verifies.<br>• C1, "Enterprise is $20k a year." against "Enterprise starts at $20 per seat per month", gives `verified=True, quote_exact`. So the parenthetical is accurate.<br>**The README lists the gap:** README:230-231.<br>**X lengths:** 275, 276 and 220 of 280 (`x_weight.py`, exit 0). |
| 2 HIGH ADR-0004 Codex row | **Partly fixed. A new HIGH in the replacement wording: finding N1** | **What is fixed:**<br>• The bare "Nothing so far" is gone.<br>• The logo is recorded at :5-8 and :35, sourced to the owner's confirmation (handoff:92, "the logo WAS made with Codex").<br>• Round 3's image comparison is the second method: both shipped logos are crops of the Codex output.<br>**"Now in the landing page and the app" holds:**<br>• The landing page (HTTP 200, 19:19Z) references `/logo.png` 11 times.<br>• The app embeds `src/receipts/ui/assets/logo.png` as a data URI (`theme.py:227-238` at `d719360`, the `/healthz` sha).<br>**"On 2026-11-15" holds in UTC:** it fits round 3's finding 2 and the app logo commit `0ed0c67` (2026-11-15T02:17:47Z).<br>**What is not fixed:** the new negative "No repository code so far: no commit carries a Codex co-author line" cites a test that cannot show it. See N1. |
| 3 MEDIUM waiver count | **Fixed** | README:489-492. Two methods agree.<br>**(a) `gh pr list --state merged` (exit 0):** 19 non-Dependabot merges, #11, #21–#32, #35, #36, #38, #43, #46 and #47. That is every such merge to date.<br>**(b) A verdict file with `VERDICT: PASS` and an mtime before `mergedAt`,** for 15 of the 19:<br>• #21 `l6-license-a5e3edf`, #23 `l6-license-followup` and #22 `w0-repair`;<br>• #24 `l3`, #26 `l5`, #27 `l4-repair`, #28 `l1-repair` and #25 `l2-repair2`;<br>• #32 `l4-constraints-repair`, #36 `gh34-r2` (27 s before merge), #38 `gh37-r2` and #29 `w2-r3`;<br>• #43 `gh42`, #47 `gh40-r2` and #46 `gh39` (8 h 44 min before merge).<br>**The other 4, from the PR bodies:**<br>• PR #11 body:16 says "`/judge` round 3: pending".<br>• PR #31 body:1 says "Fix-forward for the blind judge's FAIL on PR #30 … PR #30 was merged before the verdict at the owner's request".<br>• #35 has `gh33` verdicts r1 to r5, all FAIL.<br>**Consistent with the posts:** posts:31's "17 of the first 19" is the same set minus #30 and #31, the two with no review before merge. |
| 4 MEDIUM logo credit | **Fixed** | README:571 says "The logo was generated by the owner with OpenAI's Codex app." That is the owner's wording, verbatim from handoff:92. PR body:8 matches. |
| 5 LOW price scope | **Fixed** | **The new bullet (README:230-231)** matches `suffix_r4.py` (exit 0):<br>• `$20k`, `$20K` and `$20M` give `['$20']`, and `$1.2M` gives `['$1.2']`;<br>• `25$` and `$.99` give `[]`;<br>• C1, C2, C3, C5 and C6 verify against quotes that lack the claim's value;<br>• C4 (`$1.2M` against a `$20` quote) is not verified, which fits "can verify".<br>**README:228** now says "no sign attached". `$ 25`, `25 dollars` and `25 USD` all give `[]`, and C7 verifies.<br>**PR body:5** adds "with its gaps". |
| 6 LOW #45 source | **Source fixed. A new count error: finding N2** | **What is fixed:** the search-receipt bullet is now sourced to `rules.py`'s module docstring (`rules.py:93-96` at `d719360`, inside the docstring at :1-103: "out of scope for search receipts").<br>**What is not:** "the first seven" counts 7 tracked limits, but the list shows 7 bullets in all. See N2. |
| 7 LOW re-run parameters | **Fixed. LOW residue: finding N5** | **The arguments work:** `live_reasons.py:96` and `live_repaired.py:103` read `sys.argv[1]` as the number of runs. `live_reasons.out` and `live_repaired.out` each hold "run 1" only.<br>**The wording is fixed:** README:517-518 says "can give different counts".<br>**The scripts are unchanged:** `ast_compare.py` (exit 0) finds 3 of 3 scripts AST-equal to the scratch originals once the module docstring is set aside. |
| 8 LOW PR body sources | **Fixed as to the session and the scope call. A new MEDIUM in its time: finding N3** | **What is fixed:** PR body:11 and :21 now cite session `477932e0`. :21 says the scope widening "was the main session's call". |

## Claims that passed, and their evidence

### README (`97afe57`)
- **:225-226, "the last is by design and is described in `rules.py`'s docstring":** `rules.py:93-96`, as in R3 #6 above.
- **:228-231:** `suffix_r4.py`, as in R3 #5 above.
- **:489-492:** R3 #3 above.
- **:513-518:** R3 #7 above. "unchanged apart from their docstrings and line wrapping" is shown by `ast_compare.py`.
- **:570-571:** the "Built with" credit is unchanged and fits the new "Logo" line.

### ADR-0004 (`97afe57`)
- **:5-8:** the dated correction is at the top (I5).
  - Its sources: issue #16's title (round 3) and the owner's confirmation (handoff:92).
- **:35, Role column:** "Built no lane: L4 … (PR #27)" (round 3), and the logo sentence (R3 #2 above).
- **:35, "The owner's logo request":** the owner's confirmation.

### Scripts (`97afe57`)
- **`live_reasons.py:6`, "Also prints each dropped claim with its reason":** printed at :73-78. `live_reasons.out:1-4` shows it.
- **`pyright scripts/mellea` in the copy (exit 1):** 3 errors, at `live_pairs.py:55`, `live_reasons.py:55` (it was :56 before the docstring lost a line) and `live_repaired.py:56`. All three come from the `kwargs` inference. This matches PR body:23.

### Social posts
- **posts:20, "every number in a loosely matched quote must sit where the page has it":** re-checked because :20 changed, and it still holds.
  - Its source is `rules.py:39-46` (round 2, :123).
  - The label limit (`rules.py:47-57`) pairs a quote number with an *equal* page number under the wrong plan. So it is a label failure, not a number one.
  - The README discloses it at :227.
- **X 2/, "some quotes lacked the prices":** the same evidence as rounds 1 and 2's "didn't carry the claim's prices" (round 2, :119).
- **posts:31:** R3 #3 above.
- **Handles, links and attachments:** unchanged since round 3.

### PR #50 description draft
- **:1:** `/healthz` at 19:15Z.
- **:4, "passcode first (401), then the Keenable key (503)":** `routes.py:68` calls `check_passcode` first (:37-43, 401), and the key check is at :47-51 (503).
- **:4, "Repairs were measured locally, not yet on the deployed app":** two records agree.
  - All 3 runs in `GET /api/runs` started 01:43Z–04:31Z on 2026-11-15.
  - #46, the repair loop, merged at 17:21:20Z.
- **:5:** R3 #5 and #6 above. "which is added to #45" is judged as if text 4 were posted.
- **:7:** `ast_compare.py`.
- **:9:** ADR-0004:5-8 and :35.
- **:14, "`bin/jig` exit 0 at `97afe57`":** jig's four commands, run directly in the copy with the worktree's tools:
  - `ruff format --check .`: exit 0.
  - `ruff check .`: exit 0.
  - `pyright`: 0 errors, exit 0.
  - `pytest -q -m "not integration"`: 329 passed and 2 failed in the bare archive (exit 1).
    - The 2 were `test_harness_repair.py::test_app_import_and_create_app_load_neither_mellea_nor_litellm` and `test_settings.py::test_create_app_boots_with_an_empty_environment`.
    - Both spawn `uv run --no-sync` with only `PATH` and `HOME`, and failed with "No module named 'receipts'" because the archive has no project venv.
    - With the copy's `.venv` linked to the worktree's, both passed (exit 0). The worktree is clean at `97afe57`.
    - So 331 of the 331 selected tests pass.
  - The 9 deselected by the `integration` marker are:
    - `test_db.py::test_neon_round_trip`;
    - `test_db_constraints.py::test_duplicate_primary_key_is_rejected` and `::test_null_id_is_rejected`;
    - `test_db_constraints.py::test_null_in_required_column_is_rejected` (5 cases);
    - `test_integration_live.py::test_one_live_comparison_runs_end_to_end`.
- **:18:** the round counts are right.
  - Round 1 has 19 finding rows and ends `VERDICT: FAIL`.
  - Round 2 is README PASS and posts FAIL (its :32-33).
  - Round 3's two HIGH findings were the posts' price sentence and the Codex row.
- **:23:** pyright, above.
- **:27:** unchanged since round 3.

### Issue #45 comment
- **:3-4:** `suffix_r4.py` gives exactly the 4 outputs quoted: `['$20']`, `['$1.2']`, `[]` and `[]`. C1 reproduces "$20k a year" verifying against "$20 per seat per month".
- **:8:** README:230-231 at the PR #50 head.

## Findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| N1 | ADR-0004:35, OpenAI Codex row, "What it receives": "The owner's logo request. No repository code so far: no commit carries a Codex co-author line" | I2 (the named scope does not test the negative); I4 (one method, and it does not measure receipt) | HIGH | **The stated test is true but measures something else:**<br>• `git log --all` (exit 0): 0 of the 141 commits on local refs carry a Codex trailer.<br>• Those 141 include all 132 commits reachable from the 22 remote branch heads (`gh api …/branches`, exit 0). `git rev-list <heads> --not --all` gives 0.<br>• The trailer tally is Claude Opus 5.5 (51), Claude Fable 5.1 (49) and dependabot (4).<br>• A co-author trailer records who helped write a commit. It does not record what a tool was shown.<br>**The row's own logo is a counterexample:**<br>• The Codex-generated logo entered this repository in `0ed0c67` and its squash `002b2ae` (#36, `src/receipts/ui/assets/logo.png`, blob `cab2d06f` at `d719360`).<br>• Both commits' only trailer is "Claude Opus 5.5".<br>• So the trailer test reports no Codex involvement for the one Codex use on record.<br>**What would carry the claim:**<br>• Round 3's private check of Codex's local records (its finding 2; details withheld at the owner's request, handoff:92) found no Codex session that names this repository's path. That method does measure receipt, and it supports the claim.<br>• The same finding records one Codex setting that bears on the question (not repeated here).<br>• Neither that check nor an owner statement is cited.<br>• handoff:92 records the owner's decision to record the logo in this row. It records no owner statement that Codex received no repository code.<br>**Why HIGH, not CRITICAL:** the claim is probably true (round 3's log check), and OpenAI is an approved vendor (ADR-0004:49). | Cite a source that measures receipt, or narrow the claim to the test. For example:<br>• "No repository code so far, on the owner's word (session `477932e0`, 2026-11-15); Codex's local session logs name no repository path."<br>• Or: "No commit carries a Codex co-author line; what Codex was shown is not recorded here."<br>Either way, drop the colon that presents trailers as proof. |
| N2 | README:225-226 "The rules have known limits. Issue #45 tracks the first seven; the last is by design and is described in `rules.py`'s docstring:" | Numbers (the count does not match its visible set) | MEDIUM | **The list:** it has 7 bullets at `97afe57` (README:227-236; the bullet count is 7, exit 0). It had 6 at `ea455ef`.<br>**Read against the bullets:** "the first seven" includes the last one, which would then be both "tracked" and "by design". #45 does not track it: 0 of its 5 texts (`gh issue view 45`, exit 0) mention search receipts.<br>**Why the count can look right:** "seven" works only if bullet 2 (README:228-229) counts as two limits, bare counts and no-sign prices. #45 records those separately (the body, and the 03:52Z comment).<br>**Where it came from:** round 3's F6 said "6 of the 7 bullets" when `ea455ef` had 6 bullets. It was counting limits, not bullets. "Seven" here looks like that count plus the new suffix bullet. | "Issue #45 tracks all but the last; the last is by design …", or "the first six". |
| N3 | PR body:21 "At ~19:20 UTC (same session) the owner approved a third repair round and chose how ADR-0004 and the README record the logo." | I1 (the time is contradicted by the record) | MEDIUM | **What the record shows:**<br>• GitHub's activity API (`gh api repos/JayR1031/receipts/activity`, exit 0) gives the push of `97afe57` at 19:11:14Z. The commit date is 19:11:12Z.<br>• The round 3 verdict, whose escalation the decision answered (handoff:91-92), was saved at 19:02:46Z (file mtime).<br>• So the approval came before 19:11:12Z, and "~19:20" places it after the push it approved.<br>**The source, the handoff note, runs late elsewhere too:**<br>• handoff:89 says "~19:05 UTC: … Fixes pushed as `ea455ef`". GitHub has that push at 18:44:18Z.<br>• handoff:88 says "~18:30 UTC: round-1 credits verdict saved". The file's mtime is 18:22:05Z.<br>• handoff:93 says "~19:35 UTC: repair 3 pushed as `97afe57`", in a file last modified at 19:11:44Z.<br>**PR body:11's "~18:20 UTC"** (handoff:83) comes from the same note. Nothing contradicts it, and nothing corroborates it. | Take both times from the session transcript's message timestamps, or bound them by the record: "between the round 3 verdict (19:02Z) and the push (19:11Z)". Correct handoff:88, :89, :92 and :93 too, since later sessions read them. |
| N4 | #45 comment:5 "Observed rate: 0 of the 64 claims in the 3 runs on the deployed app use these spellings." | I6 (not re-runnable as written) | MEDIUM | **The number holds today:**<br>• `GET /api/runs` (HTTP 200, 19:21:31Z) lists 3 runs: `run-0e7ff2b1bb05` (24 claims), `run-4508f95d66ad` (23) and `run-4cbe6b629aca` (17). That is 64 claims.<br>• Round 3's `suffix_rate.py`, run on the 3 `GET /api/runs/<id>` bodies, gives "0 of 64 claims match" (exit 0).<br>• 19 of the 64 claims carry a signed price at all.<br>**It cannot be re-run as written:** the comment names no run ids, no as-of time and no pattern, so the next run on the app changes "the 3 runs".<br>**It reads as a different set:** all 3 runs started 01:43Z–04:31Z on 2026-11-15, before `d719360` went live (#46 merged at 17:21:20Z). The line before says "Checked at `d719360` (the deployed sha)", so "on the deployed app" reads as "on `d719360`". | "0 of the 64 claims in the 3 runs stored by the deployed app as of 2026-11-15 19:21 UTC (`run-0e7ff2b1bb05`, `run-4508f95d66ad`, `run-4cbe6b629aca`, all from before `d719360`), matched with `[$€£¥]\d+(?:[.,]\d+)*\s?[kKmMbB]\b\|\d\s?[$€£¥]\|[$€£¥]\.\d`." |
| N5 | `scripts/mellea/live_reasons.py:5-6` "Prints one line per run: mode, run_id, UTC start, verified/total, dropped and wall seconds." | Clarity (an incomplete field list) | LOW | `live_reasons.py:82-83` also prints `repair: {repair}`. With repairs off, that is always `repair: -`: `…/scratchpad/mellea/live_reasons.out:6` ends "wall=20.4s repair: -". The AST is unchanged (`ast_compare.py`), so the fix is to the docstring only. | "… dropped, wall seconds and `repair: -` (repairs are off)." |
| N6 | ADR-0004:35 "OpenAI Codex, CLI and desktop app (approved vendor)" | Clarity (the ADR disagrees with itself) | LOW | ADR-0004:16 approves "the vendors listed under Consequences". `openai` is listed, so the use is covered. But :49 still reads "openai — GPT family and Codex CLI", and the dated correction (:5-8) does not mention the desktop app's approval. | ":49 openai — GPT family and Codex (CLI and desktop app)", and name it in the dated correction. |
| N7 | PR body:8 "the sponsors in the product (ElevenLabs, Mellea)" | Clarity (2 of 3 listed) | LOW | The README's "Sponsors in the product" (README:556-561) has 3 entries: ElevenLabs, Mellea and Mel (:560). | "(ElevenLabs, Mellea, Mel)". |

## Outside the rubric (not a finding)

- Round 2's Luma note still applies: "Mandatory: Build Your Entire Project with Mel …". The texts accurately say that Claude Code built most of the project, and now that Codex made the logo.
- The round 3 verdict file is still marked "Do not commit as-is" (finding 2's evidence). This file quotes none of those details.
- The handoff note's times run 8–21 min late against GitHub and file records (N3). Sessions that resume from it will inherit the drift.

VERDICT: FAIL
