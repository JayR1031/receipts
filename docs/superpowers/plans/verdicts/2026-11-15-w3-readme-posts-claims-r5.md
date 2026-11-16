> Round 5 claims check by a read-only claims-judge subagent, 2026-11-15 19:30–19:36 UTC. The local clock was within 15 s of Render's `Date` header. The owner approved this narrow scope at 19:29:02Z: only the fixes for round 4's findings N1–N7. Reviewed text:
> - **The fix diff:** `git diff 97afe57 a2ecc46` (3 files, 7 insertions, 6 deletions) covers `README.md`, `docs/adr/0004-approved-ai-vendors.md` and `scripts/mellea/live_reasons.py`.
>   - **PR #50 head:** `a2ecc46`. Both `gh pr view 50` (exit 0, 19:31Z) and `git ls-remote` (exit 0, 19:31Z and 19:35Z) give it.
>   - **Base:** `d719360`. The PR is still a draft.
> - **The issue #45 comment draft** `…/scratchpad/w3/issue45-suffix-comment.md`: 8 lines, sha256 `92920b3fa7d7a42f…`, mtime 19:29:24Z, unchanged at the end.
>   - It is judged as if posted.
>   - #45 still had 4 comments at 19:35Z.
> - **The PR #50 description draft** `…/scratchpad/w3/pr50-body.md`: 29 lines, sha256 `1cd02f4e03c11db9…`, mtime 19:29:59Z, unchanged at the end.
>   - `{CI}`, `{CLAIMS}` and `{JUDGE}` are placeholders and were not checked.
>
> **Privacy:**
> - This file quotes no Codex session id, time, folder, file name or setting.
> - The Codex setting that round 4 withheld is referred to, not described.
> - No secret is printed.

# Claims verdict, round 5: fixes for round 4's N1–N7 (PR #50 at `a2ecc46`, #45 comment, PR description)

**Base and deploy.**
- `GET /healthz` at 19:32:06Z: HTTP 200, `"sha":"d719360"`, `x-receipts-mode: live`.
- `git diff --stat d719360 a2ecc46 -- src tests pyproject.toml uv.lock bin` is empty (exit 0). So the code under the texts is the deployed code.

**Sources for the owner's statements.** The session transcript `477932e0-….jsonl` was used for 3 user records only.
- **How they were selected:** `jq 'select(.type=="user" and .timestamp==$ts)'`. jq parsed the file to select them.
- **What was printed:**
  - type and timestamp for every record in those three seconds (the 3 user records, 3 `api-request` records and 2 `pr-link` records);
  - the content of the 3 user records, and nothing else.
- **The three records:**
  - **18:21:04.571Z:** "Yeah, I accept it. That's fine. …"
  - **19:09:30.372Z:** the question answers "One more repair (Recommended)", "Yes: ADR + README credit (Recommended)" and "Redact them (Recommended)".
  - **19:29:02.655Z:** the question answers "No, only the logo prompt" and "Fix + final check on the fixes (Recommended)".

**Push times.** `gh api repos/JayR1031/receipts/activity` (exit 0):
- `97afe57` was pushed at 19:11:14Z.
- `a2ecc46` was pushed at 19:29:59Z. Its commit date is 19:29:58Z.

**Re-run artifacts.** They are in the scratchpad and are not durable: `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/w3claims-r5/`
- **`web/`:** `healthz.json`, `runs.json` and `runs/run-*.json`. That is 5 GETs, all HTTP 200, between 19:32:06Z and 19:32:15Z.
- **`scripts/suffix_rate_r5.py`** (exit 0): run with `python -I` from `emptycwd/`.
- **`copy-a2ecc46/`:** made with `git archive`, with `.venv` symlinked to the worktree's venv.
- **Output files:** `pyright.out`, `pyright2.out` and `pytest.out`.
- **The worktree:** 0 changed tracked files before and after (`git status --short`).
  - No file under the worktree's `src/` or `tests/` is newer than the copy (`find -newer`, exit 0, no output).
- **Not done:**
  - `bin/jig` itself was not run, because its `uv run` can sync the shared venv. Its four commands were run directly instead.
  - No `scripts/mellea/*` was executed.
  - No POST was sent.
  - No model or Keenable call was made.
  - `~/.codex`, `~/Documents/Codex` and the handoff memory note were not read.

## Verdict per text

1. **README, ADR-0004 and `scripts/mellea/live_reasons.py` at `a2ecc46`: PASS.**
   - N1, N2, N5 and N6 are fixed.
   - There is one new LOW finding, N8.
   - README:225 depends on the #45 comment being posted before merge. See the condition below.
2. **Issue #45 comment draft: PASS.** N4 is fixed.
3. **PR #50 description draft: PASS.**
   - N3 and N7 are fixed.
   - :14 and :18 were re-checked and hold.

## Round 4 findings: status at `a2ecc46` and in the drafts

| R4 # | Status | Evidence |
|---|---|---|
| N1 HIGH: ADR-0004:35, "No repository code so far: no commit carries a Codex co-author line" | **Fixed** | **The new text** (ADR-0004:35) is "The owner's logo request. No repository code, on the owner's word (2026-11-15, 19:29 UTC)". The trailer test is gone (diff hunk at :35).<br>**The source measures receipt.** The transcript's user record at 2026-11-15T19:29:02.655Z answers the question "did Codex (the CLI or the desktop app) ever read or receive any Receipts repository code?" with "No, only the logo prompt".<br>• That option's description gave this ADR wording in advance.<br>• The question disclosed round 3's log result (no Codex session names the repository's path). It also disclosed the contrary-leaning Codex setting that round 4 withheld. So the answer was informed.<br>**I2:** the claim's scope is now its source ("on the owner's word").<br>**I4:** two methods in the record agree, the owner's statement and round 3's local-log check. The ADR presents the claim as the owner's statement, not as a verified conclusion.<br>**Order of events:** the answer was at 19:29:02Z, the commit at 19:29:58Z and the push at 19:29:59Z.<br>**"The owner's logo request"** matches "only the logo prompt".<br>**Residue:** LOW finding N8. |
| N2 MEDIUM: README:225, "Issue #45 tracks the first seven" | **Fixed, on one condition** | **The new text** (README:225) is "Issue #45 tracks all but the last; the last is by design …".<br>**The list:** 7 bullets (README:227-236; the bullet count is 7, exit 0).<br>**Bullets 1–6 against #45's 5 texts** (the body and 4 comments; `gh issue view 45`, exit 0):<br>• B1, plan labels: the 07:55:37Z comment, limit 1.<br>• B2, bare counts: the body. Unsigned prices: the 03:52:11Z comment.<br>• B3, suffixed and trailing-sign prices: in 0 of 5 texts (grep for `$20k`, `$1.2M`, `25$`, `$.99` and "suffix" exits 1). It enters #45 with the comment draft.<br>• B4, "free": the body.<br>• B5, swaps: the 07:55:37Z comment, limit 3.<br>• B6, score window: the 07:55:37Z comment, limit 2.<br>**B7, the last (search receipts):** in 0 of 5 texts (grep exits 1), which fits "by design".<br>**Today:** 5 of the 6 non-last bullets are tracked. The sixth is tracked once the comment is posted.<br>**Condition:** post the #45 comment before merging. This is the order the owner chose at 19:29:02Z ("post the #45 comment and PR description, merge"). PR body:5's "which is added to #45" depends on the same step. |
| N3 MEDIUM: PR body:21, "~19:20 UTC" | **Fixed in the PR body.** The handoff note was not checked. | **PR body:21, "At 19:09 UTC":**<br>• It matches the user record at 19:09:30.372Z: "One more repair (Recommended)" and "Yes: ADR + README credit (Recommended)". That is the third repair round and the logo wording.<br>• It comes before the `97afe57` push at 19:11:14Z, so the round 4 contradiction is gone.<br>**PR body:21, "at 19:29 UTC the owner confirmed Codex received only the logo prompt, no repository code, and approved a final check":**<br>• It matches the user record at 19:29:02.655Z.<br>• It comes before the `a2ecc46` push at 19:29:59Z.<br>**PR body:11, "at 18:21 UTC":**<br>• It matches the user record at 18:21:04.571Z ("Yeah, I accept it. That's fine."), so the time is corroborated.<br>• That record does not name the photo itself. The preceding turn would, but it was outside what this check may read. The substance passed in round 4.<br>**Not checked:** round 4 also proposed correcting handoff:88, :89, :92 and :93. The handoff note is outside the files this round may read. |
| N4 MEDIUM: #45 comment:5, not re-runnable | **Fixed** | **The new :5** names the as-of time (19:21 UTC), the 3 run ids, "all from before `d719360`", and the pattern.<br>**Re-run:**<br>• `GET /api/runs` (HTTP 200, 19:32:06Z) lists the same 3 ids, so the set is the same as round 4's 19:21:31Z GET.<br>• `GET /api/runs/<id>`, 3 of 3 HTTP 200: `run-0e7ff2b1bb05` (24 claims), `run-4508f95d66ad` (23) and `run-4cbe6b629aca` (17).<br>• `suffix_rate_r5.py` (exit 0), with the pattern copied verbatim from :5: **0 of 64** claim texts match.<br>• Controls, 6 of 6 behave: `$20k`, `$1.2M`, `25$` and `$.99` match; `$20` and `$1,000` do not.<br>• 19 of 64 claims carry a signed price, the same as round 4.<br>**"All from before `d719360`":**<br>• The runs started between 01:43:54Z and 04:31:45Z and had all finished by 04:32:56Z.<br>• `d719360` is #46's merge, at 17:21:20Z (`gh pr view 46`, exit 0).<br>**Extra false-negative check:** word suffixes such as "$20 million" or "bn" appear in 0 of 64 claims (grep exits 1). So the pattern's gap hides no claim in this set. |
| N5 LOW: `live_reasons.py:5-6`, incomplete field list | **Fixed** | **The new docstring** (:5-7) reads "… dropped, wall seconds and `repair: -` (repairs are off)".<br>**The code supports it:**<br>• :81 prints `-` when `cap.lines` is empty.<br>• `Capture` keeps only "claim repair:" messages (:36-39).<br>• `main` runs `one_run(False)` only (:94), which passes `repair_factory=None` (:55).<br>• With no factory, `_repair_failing` returns at `specialist.py:355-356`, before any "claim repair:" log (:275, :277, :362 and :370 at `a2ecc46`).<br>**Unchanged by the fix:** the diff touches only the module docstring (lines 1-12), so PR body:7's AST claim still holds. |
| N6 LOW: ADR-0004 disagrees with itself on the desktop app | **Fixed** | **The changed lines:**<br>• :49 now reads "openai — GPT family and Codex (CLI and desktop app)".<br>• :7-8 adds "(covered by the `openai` approval)".<br>**Consistent with the decision:** :16 approves "the vendors listed under Consequences".<br>**Approved:** the owner approved this fix set at 19:29:02Z ("Apply the 7 small fixes"). |
| N7 LOW: PR body:8, sponsors listed 2 of 3 | **Fixed** | **PR body:8** now reads "(ElevenLabs, Mellea, Mel)".<br>**README** "Sponsors in the product" (:556-560 at `a2ecc46`) has 3 entries: ElevenLabs, Mellea and Mel. |

## Other changed PR-description lines, re-checked

- **:14, "`bin/jig` exit 0 at `a2ecc46` (format, lint, types, tests)":** jig's four commands (`bin/jig:37`, :40, :41 and :43) were run in `copy-a2ecc46/` with the worktree's tools. API keys, `DATABASE_URL` and `DEMO_PASSCODE` were unset.
  - `ruff format --check .`: exit 0 ("88 files already formatted").
  - `ruff check .`: exit 0.
  - `pyright`: exit 0, 0 errors.
    - That was the second run, with `--pythonpath` set to the venv interpreter.
    - The first run reported 300 errors: 54 unresolved imports, plus 246 unknown types that follow from them. That is the copy's symlinked venv not being found, not the code.
  - `pytest -q -m "not integration"`: exit 0, 331 passed and 9 deselected, out of 340 collected. That is the same 331 and 9 as round 4.
    - The in-process tests imported the copy's `src` (`pythonpath = ["src"]`).
    - The 2 tests that start a `uv run --no-sync` subprocess import through the venv's editable `.pth`, which points to the worktree's `src`. The worktree is clean at `a2ecc46` and its code is identical to the copy's.
- **:18, "round 4 FAIL (one ADR-0004 sentence; posts, this description and the #45 comment PASS)":** this matches the round 4 verdict.
  - Its "Verdict per text" items 1–4 are FAIL, PASS, PASS and PASS.
  - Its only HIGH, N1, is one ADR-0004:35 sentence.

## Findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| N8 | ADR-0004:35 "No repository code, on the owner's word (2026-11-15, 19:29 UTC)" | I1 (the record id is incomplete) | LOW | **What holds:** the time matches the transcript's user record at 2026-11-15T19:29:02.655Z, and the claim is true to it.<br>**What is missing:**<br>• The ADR names no session, so a later reader cannot find the record.<br>• The PR body (:11, :21) and #45's comments (07:55:37Z, 17:20:57Z) cite their sources as "Claude Code session `477932e0`".<br>• The agreeing second method is not cited either: round 3's local-log check, in which no Codex session names this repository's path.<br>**Why not HIGH:** the claim names its source, states its scope ("on the owner's word"), and that source carries it. | "No repository code, on the owner's word (Claude Code session `477932e0`, 2026-11-15 19:29 UTC)". Optionally add "; Codex's local session logs name no repository path". That clause quotes none of the withheld details (session id, times, folder, file name). |

## Outside the rubric (not a finding)

- The caller's brief said the writer re-ran the regex "at about 19:33Z". The comment draft's mtime is 19:29:24Z, and this check began at 19:30Z. So that time cannot be right. It does not affect the drafts, which cite 19:21 UTC, the time of round 4's GET. This round's GET at 19:32:06Z shows the same 3 runs.
- The handoff note's late times (round 4, N3) were not re-checked here. Sessions that resume from it may still inherit the drift.

**Condition for this PASS:** post the #45 comment draft before merging PR #50. README:225 ("tracks all but the last") and PR body:5 ("which is added to #45") are true only once it is posted. Fill `{CI}`, `{CLAIMS}` and `{JUDGE}` before posting the description.

VERDICT: PASS
