# Claims verdict: draft body for PR #46 (issue #39, Mellea)

> **Status 2026-11-15 17:25 UTC: round 3 is PASS (0 CRITICAL, 0 HIGH, 0 MEDIUM, 4 LOW), for both the PR body and the #45 comment.** Round 1 (08:35 UTC: FAIL, 1 CRITICAL, 8 HIGH, 9 MEDIUM, 9 LOW) and round 2 (08:55 UTC: FAIL, 4 HIGH, 2 MEDIUM, 7 LOW) are below as they were; round 3 is the last section. Nothing was posted or edited.

- **Draft checked:** `S/mellea/pr46-body.md`. It has 75 lines, and its sha256 at check time was `c4c75288…ec8a0`. `draft:N` below means line N of that file. The `{CLAIMS}` placeholder (draft:70) was ignored, as asked.
- **Revisions:**
  - Head `b736d2c88b2cc7994188e23e089344fefd06f04f` on `jay/gh-39-mellea`. It is pushed: `gh pr view 46` gives `headRefOid` b736d2c, exit 0.
  - Base `origin/main` = `e844420d861e5ce8a590231ca5aef57ecbec268e`.
  - The worktree was clean before and after the check (`git status --short` printed nothing, exit 0).
- **The code was checked on copies, not in the worktree:**
  - `git archive b736d2c` into `S/claims-gh39-body/b736d2c`, and `git archive e844420 src tests` into `S/claims-gh39-body/main-e844420`.
  - The copy ran on an APFS clone of the worktree's `.venv`, with its editable `.pth` pointed at the copy's `src`.
  - The copy had no `__pycache__` outside `.venv` (`find` count 0).
  - Every Python command used `uv run --no-sync`, with `PYTHONDONTWRITEBYTECODE=1`.
- **The live scripts were not re-run.** Their outputs and logic were read:
  - `S/mellea/live_pairs.out` (sha256 `db0f20fa…`, mtime 03:16:26 -0500), `live_reasons.out` (`93eebefe…`, 03:17:22) and `live_repaired.out` (`c9007e22…`, 03:17:55).
  - All three `.err` files are 0 bytes.
- `S` = `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad`.

## Re-run evidence

| Command (cwd: worktree unless the copy is named) | Exit | Result |
|---|---|---|
| `git rev-parse HEAD origin/main` | 0 | b736d2c…, e844420… |
| `git diff --stat origin/main HEAD` | 0 | 11 files: README.md, ADR-0004, ADR-0007, pyproject.toml, `api/wiring.py`, `harness/{__init__,live,repair,specialist}.py`, `tests/test_harness_repair.py`, uv.lock |
| `git diff 5af08c1 b736d2c --stat -- src tests` | 0 | empty: the head commit changes docs only (`docs/adr/0007-mellea.md`, 1 line) |
| `git show --remerge-diff 5af08c1` | 0 | empty: the merge of main needed no conflict resolution. Parents are 4ee305a and e844420 |
| `git show --stat 4ee305a` | 0 | no files: an empty commit |
| `git log --format='%h %cd' --date=iso-strict` | 0 | 5af08c1 03:12:53 -0500; b736d2c 03:15:19 -0500 (08:15:19Z) |
| `git log -S "claim numbers not in quote: " -- src/receipts/verify/rules.py` | 0 | only e844420 (#35) |
| `git show origin/main:uv.lock \| grep -c '^\[\[package\]\]'`; same at HEAD | 0, 0 | 118 and 159. Both counts include the `receipts` project entry |
| copy: `uv run --no-sync ruff format --check .` / `ruff check .` / `pyright` | 0 / 0 / 0 | "85 files already formatted" / "All checks passed!" / "0 errors, 0 warnings". These are bin/jig's classes; `bin/jig` itself calls `uv run` without `--no-sync`, so it was not run as-is |
| copy: `uv run --no-sync python -m pytest -q -p no:cacheprovider -m "not integration" -rs`, with the API keys and `DATABASE_URL` unset | 0 | `331 passed, 9 deselected`, 0 "skip" lines |
| copy: `pytest --collect-only -m integration` | 0 | 9 tests: `test_db.py` 1, `test_db_constraints.py` 7, `test_integration_live.py` 1 |
| copy: `pytest -q -p no:cacheprovider tests/test_harness_repair.py -rs` | 0 | `13 passed` |
| copy: `ruff check --select C901 --config 'lint.mccabe.max-complexity = 0'` on the 5 changed harness and wiring files | 1 (it lists every function, as intended) | the maximum is 4, for `judge` (repair.py:133), `_repair_failing` (specialist.py:345) and `run` (specialist.py:410) |
| `python3 -I S/claims-gh39-body/fnlen.py` (AST `end_lineno - lineno + 1`, functions not in e844420) | 0 | src: `_repair_failing` specialist.py:345-371 = 27 lines, the longest. tests: `test_search_receipt_is_repaired_against_the_logged_rows` test_harness_repair.py:198-226 = 29 lines |
| copy: `env -i … ANTHROPIC_API_KEY=not-a-real-key KEENABLE_API_KEY=… DEMO_PASSCODE=… DATABASE_URL=sqlite:///… uv run --no-sync python -I -c "…create_app()…"` | 0 | `mode-probe []`: neither `mellea` nor `litellm` is in `sys.modules` |
| `gh pr checks 46` | 0 | api-image, ci-python, dependency-audit, gitleaks and leak-gate: pass |
| `gh run view 43693641788 / 43693641768 / 43693641772 --json headSha` | 0, 0, 0 | all three have `headSha` b736d2c |
| `gh run view 43693641772 --job 132749343628 --log` | 0 | "Resolved 159 packages"; "No known vulnerabilities found". The npm step printed "no package.json — skipped (reported, not passed)" |
| `git diff origin/main HEAD --stat -- .github` | 0 | empty: `security.yml` is unchanged (line 37: `uv sync && uv run pip-audit --strict --vulnerability-service osv`) |
| `gh issue view 39 --json body,author` | 0, 0 | author `JayR1031`. "Owner decision (2026-11-15): adopt Mellea (https://mellea.ai, IBM, Apache 2.0 …), a hackathon sponsor". The Acceptance section includes "README and the demo video credits name Mellea." |
| `gh issue view 33`; `gh issue view 45 --json body,comments` | 0, 0 | #33's example is `$180` in the claim, on "Pro with the biggest bucket — 18,000 credits a month.". In #45, the 07:55Z comment's item 1 is "Plan labels are not checked (fails open; also true on `main`)" |
| `gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed` | 0 | all three are true |
| `curl -sS -m 90 https://receipts-h745.onrender.com/healthz` at 08:33:24Z | 0 | `{"status":"ok","sha":"e844420",…}` |
| `grep` of the earlier transcript `~/.claude/projects/-Users-jay-Projects-receipts/fb24ba33-….jsonl` | 0 | `6bab660` appears 13 times, `a6ce697` 8 times; a tool result says "pushed: 6bab660" |
| Mellea and LiteLLM source in the worktree's `.venv` | n/a (reads) | <ul><li>`mellea/stdlib/sampling/base.py:117-131`: at most `loop_budget × concurrency_budget` generations, with concurrency 1 by default. Lines 609-650: the repair adds the failure reasons.</li><li>`mellea-0.9.0.dist-info/METADATA`: Apache-2.0, author email @ibm.com. `mellea/core/utils.py:39-46, 521-529`: the OTLP exporter and `MELLEA_LOGS_WEBHOOK` are opt-in.</li><li>`litellm/litellm_core_utils/get_model_cost_map.py:462, 746`: `LITELLM_LOCAL_MODEL_COST_MAP` turns off the price-list fetch. `litellm/llms/anthropic/common_utils.py:185`: the endpoint is `ANTHROPIC_API_BASE` or `ANTHROPIC_BASE_URL` when set, else api.anthropic.com.</li></ul> |

## Claims that pass (no finding)

- **draft:2.** The owner's decision, its date, "IBM, Apache 2.0" and "hackathon sponsor" are in the issue #39 body and author, and in `METADATA`. The "up to two rewrites" claim is `repair.py:51, 178` plus Mellea `base.py:117-131`. The pointer to ADR-0007 is right.
- **draft:5-7.** `specialist.py:345-371`; `repair.py:168-185, 216-225`; `RepairTemplateStrategy(loop_budget=2)`. Feedback carries the reason (`base.py:630-650`), and the test at `test_harness_repair.py:252` passes.
- **draft:13.** `verify_claim` is the requirement (`wiring.py:149`, `specialist.py:381`). The rule text is at `rules.py:72-92`, from e844420.
- **draft:16-17, 19-20.** `ADR-0007:13`; `AGENTS.md:104`; the pyproject diff; uv.lock (litellm 1.109.1, mellea 0.9.0); `security.yml:37`; the audit log; `ADR-0004:24`.
- **draft:29-30.** All 4 rows match `live_pairs.out:1-4`: run ids, start times, verified/total, dropped and the repair log lines.
- **draft:34-39.** `run-3cc9b768f440`, 08:17:01Z, 15/20. All 5 DROP reasons are `claim numbers not in quote`, and the quoted claims and tokens match `live_reasons.out:1-6`. The note string comes from e844420.
- **draft:41.** Issue #33's example has the same shape: a price in the claim that is not in the quote.
- **draft:43-45.** The run id, time, 20/20, the repair log line, and both claim/quote pairs match `live_repaired.out:11-14, 17`.
- **draft:50-52.** The totals across the 6 runs are 22, 22, 23, 22, 20 and 20, a range of 20-23. Both #45 examples are at `live_repaired.out:5-6, 15-16`.
- **draft:56.** Head b736d2c; 5af08c1 merges e844420 with no conflict resolution; b736d2c is docs-only.
- **draft:58-60.** These were re-run with the results above (331 passed, 9 deselected, 0 skipped; 13 passed; all 4 jig classes exit 0).
- **draft:61-62.** The values were reproduced. See the LOW and MEDIUM rows for what the draft leaves out.
- **draft:63-67.** The scope matches the 11-file diff. The lane paths are at `AGENTS.md:98, 101`.

## Findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| 1 | "The rewrites keep only what their quotes carry." (draft:47) | I4; false on its own evidence | CRITICAL | <ul><li>`live_repaired.py:67-70` prints every verified pricing claim. `live_repaired.out:17` gives `pricing failing=7 repaired=7`, `verified=20/20 dropped=0`. So 7 of the 8 printed pricing claims are rewrites, and 1 is the agent's own.</li><li>The body quotes 4 of those 8 (draft:44, 45, and 51 twice). At most 1 of the 4 can be the agent's own, so at least 3 are rewrites.</li><li>Each of the 4 carries words its quote lacks:<ul><li>"Warp's Build plan", on "$20 of agent usage included each month at API rates";</li><li>"Warp Max", on "$200 of agent usage included each month (10× Build)";</li><li>"Mel Max … hosted-AI", on "Pro with the biggest bucket — 18,000 credits a month.";</li><li>"Warp Business … on the annual plan", on "$45/user /month".</li></ul>`live_repaired.out:1-2` adds "free forever" on a quote saying "free download".</li><li>draft:51 itself concedes two of these. The sentence states the property a reviewer would merge on, and the run shows the opposite: rewrites that pass the verifier while carrying plan names and billing terms their receipts do not show. That is #45's fail-open limit, reached by a loop that rewrites until the verifier passes.</li></ul> | Delete the sentence. State what was measured, for example: "All 7 rewrites passed the verifier. At least 3 of the 4 quoted here keep plan names or terms their quote does not show (#45: labels are not checked)." |
| 2 | "The unbacked prices are gone." (draft:47) | I4 | HIGH | <ul><li>This is one run, checked by one method: the verifier itself, the same rule that produced the failures.</li><li>`live_repaired.py:70` cuts each claim to 110 characters and each quote to 130, so the artifact does not hold the full text of claim 1 ("…with no Mel cre").</li><li>`rules.py:79-82` says unsigned prices ("25 dollars", "$ 25") are not checked, so "gone" covers signed value tokens only.</li></ul> | Scope it and mark it pending: "In run-a7be7a53cba9, the verifier found every signed value token of the 8 verified pricing claims in its quote. No second check was run." |
| 3 | "Closes #39" (draft:73) | I4 | HIGH | <ul><li>Issue #39's Acceptance includes "README and the demo video credits name Mellea."</li><li>The body shows only the README credit (`README.md:489`). The `4ee305a` message says "The demo video credits for Mellea are outside this repository." No artifact shows the video credits.</li><li>The other acceptance items are carried: tests at `test_harness_repair.py:173, 232, 287` (13 passed), the live comparison at draft:29-30, and the image booting with no secrets (`api-image.yml:18` runs `docker run` with no env; job 132749343350 passed on b736d2c).</li></ul> | Name the status of the video credits with its artifact. Or use "Refs #39" and leave that item open. |
| 4 | "(`claude-sonnet-5-5` in both packs), so repair prompts go only to Anthropic, an approved vendor" (draft:10) | I1, I2, I4 | HIGH | <ul><li>The model is right (`packs/pricing.yaml:3`, `packs/positioning_seo.yaml:3`), but the draft cites neither file.</li><li>"Only to Anthropic" is a claim about where data goes, checked by reading code only (`live.py:68`, `LiteLLMBackend(model_id=f"anthropic/{model}")`). The live runs captured no traffic.</li><li>The scope leaves out three things. LiteLLM sends to `ANTHROPIC_API_BASE` or `ANTHROPIC_BASE_URL` when either is set (`litellm/llms/anthropic/common_utils.py:185`). Mellea's opt-in exporters are `OTEL_EXPORTER_OTLP_*` and `MELLEA_LOGS_WEBHOOK` (`mellea/core/utils.py:39-46, 521-529`). And nobody inspected the deployed (Render) environment.</li></ul> | Cite the pack files. State the scope: code at b736d2c, and which environment variables must be unset. Mark it "pending" until a second method agrees, such as the Render env-var names or a proxy log during a live run. |
| 5 | "**Why claims fail without repairs:** … Every one of its 5 failures was `claim numbers not in quote`, PR #35's rule" (draft:34) | I4, I3 | HIGH | <ul><li>The heading draws a general cause from one run: run-3cc9b768f440, 5 of 5 (`live_reasons.out:1-6`).</li><li>The 14 not-verified claims in the pair runs and the 14 failing claims in the repairs-on runs have no recorded reasons: `live_pairs.py:63-69` prints no reasons.</li><li>A baseline exists but is not cited, and it is mixed. In `4ee305a`, main's pre-#35 verifier dropped 0 (run-cf4acf5487cb 22/22, run-f871a88bed85 23/23). An early copy of #35's verifier also dropped 0 with repairs off (run-cca7532dc799, 20/20).</li></ul> | Scope the heading to "In run-3cc9b768f440, all 5 failures were…". Or capture the drop reasons in the pair runs and cite the earlier baseline. |
| 6 | "Mellea and LiteLLM are imported only when a claim needs repairing. `LITELLM_LOCAL_MODEL_COST_MAP=True` is set first, so `import litellm` does not fetch a price list. `create_app()` loads neither." (draft:11) | I1 | HIGH | <ul><li>The body cites no source, and `src/receipts/harness/live.py`, where this happens, is never named.</li><li>The claims are true: `repair.py:41, 169-171, 217`; `live.py:63-66`; LiteLLM `get_model_cost_map.py:462, 746`; `test_harness_repair.py:414-429` (passed); and this check's probe with dummy live keys (`mode-probe []`, exit 0).</li><li>The live runs set `LITELLM_LOCAL_MODEL_COST_MAP=True` in their environment, so they did not exercise `live.py:63`.</li></ul> | Cite `live.py:61-68`, `repair.py:169-171`, the test at `test_harness_repair.py:414`, and LiteLLM's `get_model_cost_map.py:462`. |
| 7 | "The harness emits every claim the verifier does not verify as a `dropped` event, with the verifier's note as the reason. That is what the "not verified" counts above are." (draft:32) | I1 | HIGH | <ul><li>No source is named. The claim is true at `specialist.py:385-407` and `live_pairs.py:63`, and on main at `specialist.py:315`.</li><li>Context: `verify/rules.py:98-102` documents the opposite convention ("A miss … is *not* dropped"; "L1 keys `DroppedEvent` off this"). A reader who checks the verifier will see a conflict.</li></ul> | Cite `specialist.py:396-406`, and note that it differs from the `rules.py:98-102` docstring. |
| 8 | "Render runs `main`, and this PR is not merged." (draft:53) | I1 | HIGH | <ul><li>No source is given.</li><li>It is true at check time: `curl https://receipts-h745.onrender.com/healthz` (exit 0, 08:33:24Z) gives `"sha":"e844420"`, which is `origin/main`. Handoff memory line 60 says the same.</li></ul> | Cite the healthz sha and the time it was read. |
| 9 | "The code was built at `6bab660` and `a6ce697` by the earlier Claude Code session (`fb24ba33`)." (draft:56) | I1, I3 | HIGH | <ul><li>The attribution names no source.</li><li>Two sources agree: the handoff memory's `originSessionId: fb24ba33-…` (line 7) with its line 67, and the fb24ba33 transcript ("pushed: 6bab660"; 13 and 8 mentions). The git author is the owner, with a Claude co-author line.</li></ul> | Cite the memory file and the transcript. |
| 10 | "Each run used the merged branch's code" (draft:23) | I1 | MEDIUM | <ul><li>No commit is named, and no artifact records that the tree was clean.</li><li>The runs (08:14:58Z to 08:17:36Z) straddle b736d2c's commit time (08:15:19Z). The src and tests are identical at 5af08c1 and b736d2c (`git diff --stat` empty, exit 0).</li></ul> | Write "src and tests at 5af08c1 (identical at b736d2c)", and record `git status` with the runs. |
| 11 | "a fresh temporary SQLite file (never Neon). `DATABASE_URL` was unset." (draft:23) | I1, I6 | MEDIUM | <ul><li>No artifact records the environment. The other variables that were set (`PYTHONPATH=src`, `LITELLM_LOCAL_MODEL_COST_MAP=True`) are not stated.</li><li>"Never Neon" is carried by the code regardless: `live_pairs.py:49-53` passes `SqlRunRepo(url=sqlite…)`, `wiring.py:157` uses the given repo, and `db/repo.py:121-141` reads `DATABASE_URL` only when the url is None.</li></ul> | Cite `live_pairs.py:50` and `wiring.py:157` for "never Neon". List the full run environment. |
| 12 | "The runner script is in session scratch only (`live_pairs.py`)." (draft:23) | I6 | MEDIUM | <ul><li>Three scripts produced the evidence. `live_reasons.py` (draft:34-39) and `live_repaired.py` (draft:43-45) are not named.</li><li>The arguments (2, 1 and 1, inferred because the outputs differ from the defaults at `live_*.py:82/84/85`), the exit codes and the environment are not recorded.</li><li>Scratch space is not durable.</li><li>The docstrings of `live_reasons.py:1-9` and `live_repaired.py:1-9` are copies that describe `live_pairs.py`.</li></ul> | Name all three scripts with their sha256, arguments and exit codes, or commit them under the review records. |
| 13 | "**What repaired claims look like:** … Its verified pricing claims include:" (draft:43) | I1 | MEDIUM | `live_repaired.py:67-70` prints every verified pricing claim and does not mark the rewrites. Of the 8 printed, 7 are rewrites and 1 is not, and which one was not recorded. The examples are presented as rewrites without that evidence. | Say "7 of these 8 are rewrites; which 7 was not recorded". Or log the repaired claims in `_repair_failing` for the run. |
| 14 | "27.5 s" / "19.5 s" / "19.7 s" / "21.1 s" (draft:29-30) | Numbers | MEDIUM | The draft does not say what the seconds measure. `live_pairs.py:55-58` times from `service.start()` to the end of the event stream, and leaves out `service.wait()`. | Write "wall time from start to the last event (`live_pairs.py:55-58`)". |
| 15 | "**Lock size:** 118 packages on `main`, 159 here." (draft:18) | I6, Numbers | MEDIUM | No command is given. It was reproduced with `grep -c '^\[\[package\]\]' uv.lock`: 118 at origin/main, 159 at HEAD, exit 0. Both counts include the `receipts` project entry. The CI log says "Resolved 159 packages". | Quote the command, and say that the count includes the project entry. |
| 16 | "Ruff C901 on the changed harness and wiring files tops out at 4 (`run`, `judge`, `_repair_failing`). The longest new function is `_repair_failing` at 27 lines." (draft:62) | I6, Numbers | MEDIUM | <ul><li>No command or counting method is given. Both values were reproduced (see Re-run evidence).</li><li>"Longest new function" holds for src only. A new test, `test_harness_repair.py:198-226`, is 29 lines.</li></ul> | Quote the ruff command and the line rule ("def to last line"), and write "longest new function in src". |
| 17 | "the earlier session's `4ee305a` message reports a red run first, 14 of 14 guard sabotages red, and a boot check of the image with no secrets. This session did not re-run them" (draft:68) | I1 | MEDIUM | <ul><li>This misreports the relayed record. `4ee305a` says "Boot stand-in: uv sync --frozen --no-default-groups on Python 3.12, then uvicorn under env -i" and "Docker daemon was not running locally; the api-image workflow on the PR is the real check". It was not an image boot.</li><li>The relayed results are at 6bab660, before main was merged in, and the draft does not say so.</li><li>An image boot with no secrets did run on b736d2c: `api-image.yml:18`, job 132749343350, plus `tests/test_settings.py:76`.</li></ul> | Relay what `4ee305a` actually says, at 6bab660. Cite the api-image job for the image boot. |
| 18 | "corrected ADR-0007's line on #35 in `b736d2c`" (draft:56) | I5 | MEDIUM | <ul><li>`ADR-0007:25` was rewritten in place, with no dated correction note at the top or in the line (`ADR-0007:3` is unchanged).</li><li>The repair prompt still states the superseded wording: `repair.py:66-67`, "Every price, percentage or other number in the claim text must also be in the quote". The rule is value tokens only.</li></ul> | Add a dated note to ADR-0007, for example "Corrected 2026-11-15: #35 merged as e844420; rule is value tokens". Track the prompt wording, or say why it stays broader. |
| 19 | "**CI:** api-image, ci-python and security (dependency audit, gitleaks, leak gate) passed on `b736d2c`." (draft:61); "It passed on `b736d2c`" (draft:19) | I1 | LOW | <ul><li>True: runs 43693641788, 43693641768 and 43693641772, all with `headSha` b736d2c. But no run ids are given.</li><li>Within dependency-audit, the npm step printed "no package.json — skipped (reported, not passed)", and that step is not named.</li></ul> | Add the run ids. Name the npm step as skipped because there is no package.json. |
| 20 | "the runner clears the verify fields and keeps `about`" (draft:9) | I1 | LOW | The runner clears the verify fields (`specialist.py:251-253, 263`), but `about` is kept by `judge` (`repair.py:145`). The behaviour is true, and the test at `test_harness_repair.py:278` passes. | Write "`judge` keeps `about` (`repair.py:145`)". |
| 21 | "Repairs stop at the pack's `timeout_s`." (draft:8) | clarity | LOW | The deadline is counted from the start of the specialist's run (`specialist.py:413`), so repairs get only the time the agent left (`specialist.py:358-363`). | Add "counted from the start of the run". |
| 22 | "each domain logs `claim repair: <domain> failing=N repaired=M`" (draft:12) | clarity | LOW | That line is not logged when the budget is spent (`specialist.py:362` logs "skipped" instead), nor in repairs-off runs (`specialist.py:355`). | Add "when repairs are on and time remains". |
| 23 | "`4ee305a` is an empty status commit, squashed at merge." (draft:56) | clarity | LOW | The commit is empty (`git show --stat`, exit 0). But "squashed at merge" is an intent, not a fact: the repo allows squash, merge and rebase (`gh repo view`: all three true). | Write "to be squashed at merge". |
| 24 | "(Mel vs Warp, this session, 2026-11-15)" (draft:22) | I1 | LOW | The outputs record only `HH:MM:SSZ` (`live_pairs.py:54`). The date comes from the file mtimes (2026-11-15 03:16-03:17 -0500). | Print the full ISO date in the run output, or cite the mtimes. |
| 25 | "The verifier stays the only thing that can mark a claim verified." (draft:2) | I4 | LOW | True. The code is at `specialist.py:251-253, 385-407`, and the tests at `test_harness_repair.py:266, 287` pass. The draft cites only the ADR for this verdict. | Cite the two tests next to the code. |
| 26 | "`uv run pytest -q -p no:cacheprovider -m "not integration" -rs`: 331 passed…"; "`tests/test_harness_repair.py` alone: 13 passed." (draft:59-60) | I1 | LOW | The values reproduce (exit 0, 331/9/0 and 13). The draft gives no exit code, and the second command is not quoted in full. | Add "exit 0" and the full command. |
| 27 | "totals vary from 20 to 23 claims per run" (draft:50) | Numbers | LOW | True across 6 runs (22, 22, 23, 22, 20, 20), but the set (6 runs) is left implicit. | Write "across these 6 runs". |

VERDICT: FAIL

---

## Round 2 (2026-11-15 08:55 UTC)

- **Drafts checked:**
  - Body: `S/mellea/pr46-body.md`, 118 lines, sha256 `a9c74434…1e3c`. `body:N` means line N. The `{CLAIMS}` placeholder (body:111) is left for the caller.
  - Issue #45 comment: `S/mellea/issue45-mellea.md`, 17 lines, sha256 `2961c734…f0e2`. `c45:N` means line N. It is not posted yet: #45 still has 3 comments (`gh issue view 45 --json comments`, exit 0).
- **Revisions:**
  - Head `f473eaea67425b0f4efd055cd41c210f200c802b` is pushed: after `git fetch`, `HEAD` and `origin/jay/gh-39-mellea` agree. `origin/main` is still e844420.
  - f473eae changes only `docs/adr/0007-mellea.md` (`git show --stat`). `git diff 5af08c1 f473eae --stat -- src tests` is empty, exit 0.
- **The owner's answers:** session record `477932e0` holds the question at line 3852 (08:38:16Z) and the answers at line 3853 (08:45:57.308Z): "Merge, record the risk (Recommended)" and "Yes, they do".

### Round 2 re-run evidence (new)

| Command | Exit | Result |
|---|---|---|
| `gh pr checks 46`; `gh run view 43696092615 / 43696092606 / 43696092614 --json headSha` | 0 | 5 of 5 pass. All three runs have `headSha` f473eae |
| Version compare of `[[package]]` blocks in `git show origin/main:uv.lock` and `f473eae:uv.lock` (`python3 -I`) | 0 | Exactly 2 versions change: `huggingface-hub` 2.4.0 → 1.33.0 and `python-dateutil` 4.0.0 → 2.9.0.post0. 0 packages are removed |
| `grep -rn "huggingface\|dateutil" src/receipts` | 1 | no match |
| `sed -n 170,190p tests/test_harness_repair.py` | 0 | The happy-path test asserts 2 verified claims with the same `GOOD_QUOTE` (lines 182-186) |
| `sed -n 455,475p …/litellm/litellm_core_utils/get_model_cost_map.py` | 0 | With the env var set, it loads `load_local_model_cost_map_with_revision()` |
| Session record `477932e0`, lines 3659, 3728, 3751, 3756 | n/a (read) | <ul><li>The live commands: `source ~/.zshenv; unset DATABASE_URL; LITELLM_LOCAL_MODEL_COST_MAP=True PYTHONPATH=src .venv/bin/python …/live_pairs.py 2`, which exited 0 (line 3728).</li><li>Then `live_reasons.py 1` and `live_repaired.py 1`. For those two, only a traceback count was recorded, not an exit code.</li></ul> |
| Session record `477932e0`, line 3559 | n/a (read) | The Render API gave "deploy: live e844420 2026-11-15T07:58:07.335144Z", then `/healthz` gave `"sha":"e844420"` |
| Blind verdict `docs/superpowers/plans/verdicts/2026-11-15-gh39.md` | n/a (read) | <ul><li>VERDICT: PASS. Findings 1-7 are MEDIUM and 8-11 are LOW.</li><li>Sabotage: 25 of 34 red. The 9 green are S02, S06, S09, S11, S12, S18a, S30, S32 and S33.</li><li>A LiteLLM mock reply carrying `"verified": true` came back `False`.</li></ul> |
| `stat` of `~/Projects/receipts-drafts/receipts-demo-narrated.mp4` | 0 | 6,181,398 bytes, modified 2026-11-14T21:21:05-0500 (02:21:05Z). That is 12 minutes before issue #39 was created (02:33:27Z) |
| `ffprobe` (duration); `ffmpeg -sseof -1` (last frame); `ffmpeg` with `fps=1/2,tile=10x6`, and `fps=1/4` over the last 20 s | 0, 0, 0, 0 | <ul><li>The video is 120 s long.</li><li>The last frame reads "Narration by ElevenLabs · Built with Claude Code and Mel".</li><li>No frame on the 2-second sheet names Mellea.</li><li>The frames are in `S/claims-gh39-body/video-frames/`.</li></ul> |
| `grep -ril mellea ~/Projects/receipts-drafts` | 1 | no match in the demo script, the submission text or the architecture file |

### Round 1 findings: status

| R1 # | Status in round 2 |
|---|---|
| 1 (CRITICAL) | Resolved. The sentence is gone, and the risk is stated at body:22-25. The new count problem is round-2 #2 and #3 |
| 2 (HIGH) | Resolved at body:65, which is scoped to currency-signed prices in the 8 printed claims. It says the verifier checks these and that unsigned prices are not checked |
| 3 (HIGH) | **Not resolved.** It rests on the owner's word, and the only video file on record contradicts it (round-2 #1) |
| 4 (HIGH) | Resolved at body:13-14: checked by code only, marked pending, with the scope named |
| 5 (HIGH) | Resolved at body:50 and 57 |
| 6 (HIGH) | Sources are now cited, but one sentence is false as worded (round-2 #5) |
| 7 (HIGH) | Resolved at body:48 |
| 8 (HIGH) | Resolved at body:69. The record line is not cited (round-2 #12) |
| 9 (HIGH) | Resolved at body:82 |
| 10 | Resolved at body:30. The tree's state at run time is still not recorded |
| 11 | Resolved at body:31-32. It matches record line 3659 |
| 12 | Resolved at body:34-39. For the exit codes, see round-2 #12 |
| 13, 14, 15, 17, 18 | Resolved at body:59, 33, 74 and 108-109. For #18, the dated note is at ADR-0007:5 at f473eae, and body:20 discloses the broader prompt |
| 16 | Resolved at body:94-95. The line-counting rule is still unstated; not raised again |
| 19 | Resolved for b736d2c at body:76 and 91. The head's runs are not cited (round-2 #8) |
| 20 | Resolved in substance at body:11. For the wording, see round-2 #10 |
| 21, 22, 23, 25, 26, 27 | Resolved at body:10, 19, 83, 4, 88-89 and 67 |
| 24 | Resolved at body:29. The per-run times were dropped (round-2 #9) |

### Round 2 findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| 1 | Body: "The owner confirmed in this session that the demo video's credits name Mellea; the video is outside this repository. With the README credit (`README.md:489`), that meets issue #39's last acceptance item." (body:114), and "Closes #39" (body:116) | I4 | HIGH | <ul><li>The two methods disagree.</li><li>The owner answered "Yes, they do" (record line 3853) after being told "The video is outside the repo, so I can't check it" (line 3852).</li><li>The video named in handoff memory line 13, `~/Projects/receipts-drafts/receipts-demo-narrated.mp4`, was last written at 02:21:05Z. That is 12 minutes before issue #39 existed.</li><li>Its last frame (`ffmpeg -sseof -1`, exit 0) reads "Narration by ElevenLabs · Built with Claude Code and Mel". No frame on a 2-second contact sheet names Mellea, and `grep -ril mellea ~/Projects/receipts-drafts` exits 1.</li><li>The owner may mean another cut, but the body does not name one.</li></ul> | Show the owner `S/claims-gh39-body/video-frames/last-frame.png` and ask which cut (file or URL) names Mellea. Cite that cut's credits frame. If there is none, use "Refs #39" and leave the video credit open. Either way, cite record line 3853 |
| 2 | Body: "In the live run below, the four printed pricing claims inspected each do; at least 3 of them are rewrites." (body:25), and "Four of them carry a plan name or term their quote does not show (the risk above)" (body:59) | Numbers, I2 | HIGH | <ul><li>The count understates the artifact. Two more claims carry a plan name their quote lacks:<ul><li>`live_repaired.out:7-8`: "Mel Business includes 1,500 hosted-AI credits a month per seat, shared by the whole team." on the quote "1,500 hosted-AI credits a month per seat, shared by the whole team".</li><li>`live_repaired.out:9-10`: "Warp Free includes additional agent usage at pay-as-you-go rates." on the quote "Additional agent usage at pay-as-you-go rates".</li></ul>Both claims and both quotes are shorter than the 110/130-character cut, so they are complete.</li><li>With the 4 already listed, at least 6 of the 8 carry a plan name their quote does not show. Only 1 of the 8 is not a rewrite, so at least 5 of those 6 are rewrites.</li><li>The other 2 add terms their quotes lack: "free forever" on "a free download" (`:1-2`), and "credits a month" on "1,500 hosted-AI credits" (`:3-4`).</li><li>"Inspected" leaves out half of an 8-line artifact, and this is the risk the owner chose to record.</li></ul> | Count all 8: "At least 6 of the 8 carry a plan name their quote does not show, and at least 5 of those are rewrites. The other 2 add a term ('forever'; credits 'a month')." List all six, or name the two added |
| 3 | Comment: "Four of the printed claims carry a plan name or term their quote does not show:" (c45:5), and "At least 3 of these 4 are rewrites." (c45:11) | Numbers | HIGH | The evidence is the same as #2. This comment is the risk record that #45 keeps, and "4 of 8" understates the measured "at least 6 of 8, of which at least 5 are rewrites". | Apply the same fix as #2 |
| 4 | Comment: "The owner chose to merge it with these recorded (Claude Code session `477932e0`, 08:45:57 UTC)." (c45:1) | I3 | HIGH | <ul><li>"These" means both limits.</li><li>The question the owner answered (record line 3852) names only plan labels ("the verifier doesn't check plan labels … carry plan names their quotes don't show"). Its options never mention duplicate receipts.</li><li>Limit 2 comes from the blind review's finding 11, which says "Decide (owner) whether a repaired claim that duplicates an existing receipt counts". The owner has not decided it.</li></ul> | Write: "The owner chose to merge with limit 1 recorded (…). Limit 2 comes from the blind review (finding 11) and is open for the owner." Or put it to the owner first. body:25 attributes only the label risk to the owner, and is fine |
| 5 | Body: "Mellea and LiteLLM are imported only inside `litellm_backend` (`live.py:61-68`), which sets `LITELLM_LOCAL_MODEL_COST_MAP=True` first." (body:16), and "The repairer reaches the backend only when a claim fails (`repair.py:169-171`)." (body:17) | I1 | MEDIUM | <ul><li>False as worded for Mellea. `MelleaClaimRepairer.__call__` imports Mellea at `repair.py:169-171`, `_ainstruct` imports it at `:211`, and `_validator` at `:217`. All of these run before the backend is built at `:176`.</li><li>The cited `repair.py:169-171` are those Mellea imports, not a backend call or a gate. The gate is `specialist.py:355-367`.</li><li>The conclusion, nothing loads at import, still holds: `test_harness_repair.py:414-429` passes, the round-1 probe printed `[]`, and the blind review's probes agree.</li></ul> | Write: "Mellea is imported in `MelleaClaimRepairer.__call__` (`repair.py:169-171, 211, 217`), and LiteLLM in `litellm_backend` (`live.py:63-66`). The runner calls the repairer only for failing claims (`specialist.py:355-367`)." |
| 6 | Body: "**PASS**, 7 MEDIUM and 4 LOW, all missing evidence or test gaps, none wrong behaviour." (body:97) | I1 | MEDIUM | <ul><li>The counts are right: in `gh39.md`, findings 1-7 are MEDIUM and 8-11 are LOW.</li><li>"None wrong behaviour" is not in the verdict. Its finding 11 says nothing removes a duplicated receipt, and "That raises verified/total, the acceptance metric". Its finding 8 says the runner passes a changed `about` or `domain` through from any other repairer.</li><li>The body's own risk section (body:22-25) also describes a behaviour.</li></ul> | Drop "none wrong behaviour", or quote the verdict's own words |
| 7 | Body: "**Not fixed here, follow-ups:** …" (body:99-104) | clarity | LOW | Two blind-review findings are neither fixed nor listed. Finding 5: no test is named as watched failing. Finding 7: ADR-0007:18's "confirmed live … rejected the first answer and accepted the repair" has no artifact. | List them |
| 8 | Body: "It passed on `b736d2c` (run 43693641772)" (body:76), "**Gates on `b736d2c`**" (body:86) and "**CI on `b736d2c`:**" (body:91) | I1 | LOW | The head is f473eae (body:81). CI also ran there and passed: runs 43696092615, 43696092606 and 43696092614, all with `headSha` f473eae (`gh run view`, exit 0). | Cite the head's runs as well |
| 9 | Body: the table rows (body:45-46) | I1 | LOW | The per-run UTC start times were dropped, leaving only a range (body:29). Issue #39's acceptance asks for "run ids and UTC times cited". The times are in `live_pairs.out:1-4` and `live_reasons.out:6`. | Put each run's start time back |
| 10 | Body: "Mellea's `judge` keeps the original claim's `about`" (body:11) | clarity | LOW | `judge` is this repo's function (`repair.py:133`), not Mellea's. | Write "`judge` in `repair.py:133-149`" |
| 11 | "Mellea rewrites a failing claim until the verifier accepts it" (body:23), and "until `verify_claim` accepts it" (c45:3) | clarity | LOW | Mellea makes at most two model calls (`repair.py:51, 178`), within the pack's time budget (`specialist.py:413`). The body states the cap at body:9; the comment never does. | Write "at most twice, until …" |
| 12 | Body: "Its deploy of `e844420` went live at 07:58Z" (body:69), and "None printed a traceback." (body:39) | I1 | LOW | <ul><li>Both are true in the session record but not cited.</li><li>Line 3559 has the Render API's "live e844420 2026-11-15T07:58:07Z".</li><li>Lines 3659 and 3728 show live_pairs exiting 0. Lines 3751 and 3756 record only a traceback count for the other two scripts, with no exit code.</li><li>The `.err` files are 0 bytes.</li></ul> | Cite the record lines and the `.err` sizes |
| 13 | Comment: "verdict `2026-11-15-gh39`, LOW 11" (c45:13), and the run evidence (c45:5) | I6 | LOW | Readers of #45 can open neither. The verdict is untracked, and the run's script and output are in session scratch. | Point to PR #46's body for how the run was made, and say the verdict is committed later (W3) |

**Per draft:** the body FAILS (#1 and #2 are HIGH). The #45 comment FAILS (#3 and #4 are HIGH). The comment is posted first, so fix it before the body.

VERDICT: FAIL

---

## Round 3 (2026-11-15 17:25 UTC)

- **Drafts checked:**
  - Body: `S/mellea/pr46-body.md`, 136 lines, sha256 `bd5f7d75…019c`. `body:N` means line N. `{CLAIMS}` (body:127) is unfilled.
  - #45 comment: `S/mellea/issue45-mellea.md`, 21 lines, sha256 `559dbc12…eaf9`. `c45:N` means line N. It is not posted yet: #45 still has 3 comments (`gh issue view 45`, exit 0).
- **Revisions:**
  - Head is still `f473eae` (`git fetch`, then `git rev-parse HEAD origin/jay/gh-39-mellea`), and `origin/main` is still e844420.
  - PR #46 is a draft and open; issue #39 is open.
  - `grep -nE "Closes|Fixes|Resolves|none wrong|until the verifier accepts|Four of"` on both drafts exits 1, so none of the superseded phrasing is left.
- **The owner's answers:** record `477932e0` holds the questions at line 3983 (asked 08:56:20Z) and the answers at line 3984 (17:16:32.621Z): "Refs #39, credit later", "Yes, merge (Recommended)" and "Record, fix as follow-up (Recommended)". The questions stated the video's actual credit line, "at least 6 of the 8 … at least 5 of the 6 are Mellea rewrites", and the duplicate-receipt effect.

### Round 3 re-run evidence (new)

| Command | Exit | Result |
|---|---|---|
| `gh run view 43696092614 --job 132756824477 --log` (dependency-audit at f473eae) | 0 | "Resolved 159 packages"; "No known vulnerabilities found"; the npm step printed "no package.json — skipped (reported, not passed)" |
| `grep -rn "receipts-demo"` over the memory folder, `docs/` and both READMEs | 0 | Only handoff memory line 13 names a video (`receipts-demo-narrated.mp4`); the other hits are this verdict |
| `ls -la ~/Projects/receipts-drafts/*.mp4`; `find ~/Projects ~/Movies ~/Desktop ~/Downloads -maxdepth 3 -iname "*receipts*.mp4" -newer …narrated.mp4` | 0, 0 | Two files: `receipts-demo-narrated.mp4` (2026-11-14 21:21 -0500) and `receipts-demo.mp4` (20:40 -0500). No newer cut was found |
| `ffmpeg -sseof -1` on `receipts-demo.mp4` | 0 | The last frame ends with the tracks line. It has no credits line and no Mellea (`S/claims-gh39-body/video-frames/plain-last-frame.png`) |
| `live_repaired.out:1-16` against body:67-77 and c45:6-13 | n/a (read) | All 8 claim/quote pairs are quoted faithfully. The 6 plan-name cases and the 2 added-term cases match the round-2 analysis |
| `sed -n 3983,3984p` of the session record | n/a (read) | As described above |

### Round 2 findings: status

| R2 # | Status in round 3 |
|---|---|
| 1 (HIGH) | Resolved. The body ends "Refs #39" (body:134). It quotes the video's credit line (body:130) and cites the owner's choice at line 3984 (body:132). There is no closing keyword in either draft |
| 2 (HIGH) | Resolved. All 8 are counted and listed (body:24, 65-77): 6 with a plan name, at least 5 of them rewrites, and 2 with an added term. Both decisions are cited (body:27-28) |
| 3 (HIGH) | Resolved (c45:5-13) |
| 4 (HIGH) | Resolved. Limit 1 is attributed to the answers at 08:45:57 and 17:16:32 (c45:15), and limit 2 to the answer at 17:16:32 (c45:17), which matches record lines 3853 and 3984 |
| 5 (MEDIUM) | Resolved (body:15-16). The cited lines match `repair.py:169-171, 211, 217`, `live.py:61-68` and `specialist.py:355-367` |
| 6 (MEDIUM) | Resolved (body:111) |
| 7, 8, 9, 10, 11, 13 | Resolved at body:118-119, 90 and 105, 51-52 and 56 and 65, 11, 22 with c45:3, and c45:1 |
| 12 | Resolved for the deploy (body:83, line 3559) and the stderr sizes (body:45). The exit-status line is still uncited (round-3 #4) |

### Round 3 findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| 1 | Body: "The only demo video on record (`~/Projects/receipts-drafts/receipts-demo-narrated.mp4`, saved 02:21Z, before #39 existed) ends "Narration by ElevenLabs · Built with Claude Code and Mel"." (body:130) | I2 | LOW | <ul><li>The draft does not say what "on record" means.</li><li>It holds for the project's records: only handoff memory line 13 names a video.</li><li>An older file sits in the same folder, `receipts-demo.mp4` (20:40 -0500). It has no Mellea either, so the outcome is the same under the wider reading.</li><li>PR readers cannot open a local path.</li></ul> | Write "the video named in the project's handoff notes", and add that the older cut in the same folder has no Mellea either |
| 2 | Body: "the owner chose "Merge, record the risk" on my count of 3 of 4." (body:27) | clarity | LOW | The body is posted from the owner's account, so "my" reads as the owner's count. The count was the session's (record line 3852). | Write "on the session's count of 3 of 4" |
| 3 | Comment: "To decide: … For 2: count claims with identical receipts once." (c45:19-21) | clarity | LOW | The owner has already chosen "Record, fix as follow-up" (line 3984). That option's description reads "record it in #45 as an open item to count identical receipts once" (line 3983). For 2, then, the direction is decided and only the fix is open. | Label it "Follow-up (owner's choice, 17:16:32 UTC): count claims with identical receipts once" |
| 4 | Body: "Only `live_pairs.py`'s exit status, 0, was recorded." (body:45) | I1 | LOW | True: record line 3728 has "exit=0" for `live_pairs.py 2`. But it is not cited, while the other record facts now are. | Cite record line 3728 |

**Per draft:** the body PASSES (3 LOW: #1, #2, #4). The #45 comment PASSES (1 LOW: #3).

**`{CLAIMS}` fill (body:127):** `PASS, round 3 (0 HIGH, 0 MEDIUM, 4 LOW): docs/superpowers/plans/verdicts/2026-11-15-gh39-body-claims.md (not committed yet)`. That line only becomes true once the box is ticked: change `- [ ]` to `- [x]` when filling it.

VERDICT: PASS
