> Saved by the main session from the read-only judge's report.

# Blind judge: PR #50, task `w3-credits` (2026-11-15)

Head `ea455ef`, base `d719360` (main; `/healthz` on the deployed app reports this sha). Six paths changed: `README.md`, `docs/adr/0004-approved-ai-vendors.md`, `docs/assets/miami-ai-hackathon.jpg`, and `scripts/mellea/live_pairs.py`, `live_reasons.py`, `live_repaired.py`.

| # | Severity | Finding | Citation (`file:line` or command + exit) | Fix |
|---|---|---|---|---|
| 1 | MEDIUM | **The scope widening is recorded only in this ticket.** Two of the changed path groups are covered only by the ticket's asks 3 and 4: `docs/adr/0004-approved-ai-vendors.md` and `scripts/mellea/*.py`. The only written W3 brief lists `scripts/` and "ADRs" under `Forbidden:`. The plan's w3 scope is `["README.md", "docs/submission/**", "docs/assets/**"]`. Measured against the ticket I was given, every path is in scope, so this is not a scope breach. | `/Users/jay/Projects/receipts/docs/superpowers/briefs/W3-ship.md:25-26` (untracked, main checkout); `docs/superpowers/plans/2026-11-14-w0-foundations-and-w1-lanes.md:199` | Record the owner's ask for the ADR and the scripts in the PR body, or amend the brief or plan scope. |
| 2 | MEDIUM | **The PR body says the PR is "README only", which the diff disproves.** The body says "W3 wrap-up, README only". The diff also changes ADR-0004, adds the image and adds three scripts (291 lines). The PR title names neither the ADR nor the scripts. | `gh pr view 50` exit 0 (body); `git diff --stat origin/main...HEAD` exit 0 (6 files, 398+/32-) | Replace the draft body with one that names all six paths. |
| 3 | MEDIUM | **No test is named as watched failing, and the report doesn't say none applies.** The executable addition is the three runner scripts, which have no test. pytest collects only `tests/`. I cannot point to any test that would fail without this change. | `gh pr view 50` exit 0 (no test named); `pyproject.toml` `testpaths = ["tests"]` | State in the PR body: "no test: docs, image and paid live-run scripts", plus the command that re-ran the README's verifier outputs. |
| 4 | LOW | **The re-run instructions don't reproduce the recorded runs.** The README gives no argument for `live_reasons.py` or `live_repaired.py`, and both default to 2 runs. PR #46's body says the recorded runs used argument 1, and the saved outputs show only "run 1". Following the README spends twice the recorded credits. | `README.md:507-508`; `scripts/mellea/live_reasons.py:97`; `scripts/mellea/live_repaired.py:103` | Write `live_reasons.py 1` and `live_repaired.py 1`. |
| 5 | LOW | **The scripts fail pyright, and `bin/jig` never type-checks them.** `kwargs = {} if repairs_on else {"repair_factory": None}` is inferred as `dict[str, None]`, and pyright checks it against `model_factory: ModelFactory` (`src/receipts/api/wiring.py:130`). Runtime is unaffected, because only the `repair_factory` key is passed and `wiring.py:133` accepts `None`. Pyright's include list is `["src", "tests"]`, so jig's `types ok` does not cover `scripts/`. | `uv run pyright scripts/mellea/*.py` exit 1, 3 errors at `live_pairs.py:55`, `live_reasons.py:56`, `live_repaired.py:56`; `pyproject.toml` `[tool.pyright] include` | Pass `repair_factory=` explicitly. Note that this changes code the README says is "unchanged apart from docstrings". |
| 6 | LOW | **One docstring describes output the script never prints.** It says the script prints "`claim repair:` log lines (repairs-on runs only)", but `live_reasons.py` only ever runs with repairs off. | `scripts/mellea/live_reasons.py:5-7`, `:94` | Drop that clause from this script's docstring. |

## Checks with no finding

**Gates**
- `bin/jig` exit 0: format, lint, types and tests all ok. It wiped `__pycache__` first (`bin/jig:92-94`).
- `uv run pytest -q -m "not integration" -rs -p no:cacheprovider` exit 0: 331 passed, 9 deselected, 0 skipped.
- `gh pr checks 50` exit 0: 5 of 5 checks pass (api-image, ci-python, dependency-audit, gitleaks, leak-gate).
- `python3 -I scripts/leak_gate/check_tracked.py` exit 0.
- Gitleaks still blocks: `--exit-code 1` at `.github/workflows/security.yml:22`, unchanged.
- `git diff --quiet origin/main...HEAD -- src tests pyproject.toml uv.lock` exit 0, so no frozen file and no test is touched (AGENTS.md:104).

**Verifier section matches `rules.py` at `d719360`**
- Table rows `README.md:212-214` match `rules.py:33-46` and `:72-79`.
- The known limits at `README.md:226-232` match `rules.py:47-71`, `:86-92` and `:95-96`.
- I re-ran all 7 README examples through `verify_claim` (`uv run python …/judge/readme_cases.py`, exit 0). All 7 verified flags, methods and notes match the README text exactly.
- Each case, or a close variant, is in `tests/test_verify.py` or `tests/test_verify_claim_numbers.py` (for example `test_verify_claim_numbers.py:64` for `$18`).

**Status box (`README.md:20-23`)**
- Demo fallback: `wiring.py:107-118` and `:222-223`.
- The UI replays the demo with no setup: `wiring.py:308`.
- `POST /api/runs` checks the passcode first (401), then the Keenable key (503): `routes.py:68-69`.
- Up to two Mellea rewrites: `repair.py:51` (`MAX_REPAIRS = 2`).
- The deployed app is live, checked by a second method: `curl -sS -D - https://receipts-h745.onrender.com/healthz` exit 0 returned HTTP 200, `x-receipts-mode: live` and `"sha":"d719360"`.

**Mel vs Warp numbers**
- All 6 run ids, and every count and wall time, match the saved outputs (`scratchpad/mellea/live_{pairs,reasons,repaired}.out`) and PR #46's body.
- The code that produced them has the same `src` as main: `git diff --quiet 5af08c1 d719360 -- src` exit 0, which supports "with the code now on `main`".
- "Unchanged apart from docstrings": the committed scripts are AST-equal to the scratch originals with docstrings ignored, 3 of 3 (`ast_cmp.py` exit 0 each). The originals' modification times are 08:14:33Z to 08:17:35Z, at or before each run's start.

**Event photo**
- It is a 969x1107 baseline JPEG. Its only segments are APP0 (JFIF), DQT, DHT, SOF0 and SOS.
- 0 Exif, XMP, ICC, Photoshop/IPTC or comment segments.
- `sips -g all` returned 0 matches for gps, make, model, software or creation.
- Viewed: no people. The screen's bottom strip is blurred to featureless blobs; at 2.5x enlargement no QR structure is visible.
- Limit of this check: no QR decoder is installed (`zbarimg` and `cv2` are absent), so "QR codes unreadable" rests on visual inspection only.

**Credits**
- 15 of 15 named technologies and 4 of 4 event facts from the ticket appear at `README.md:545-563`.
- The libraries match `pyproject.toml` dependencies, and `claude-sonnet-5-5` is at `src/receipts/packs/pricing.yaml:3`.

**ADR-0004 builder roles**
- PR #26 is gh-17 (L5) and PR #27 is gh-16 (L4). Issue #16 is titled "(Claude Code)".
- PR #47's body credits Mel with 4 commits.
- The commits in PRs #26 and #27 without a Claude trailer are only merge commits (1 of 2 and 2 of 9).
- The correction sits at the top of the ADR and the table rows themselves were edited, so the record is fixed at the top (rubric 7).
- The spec's older builder table (`specs/…-receipts-design.md:81`) is already overridden by the pointer at `:12` and the plan's scope-cut row at plan `:26`.

**Practice applied:** a verdict needs two independent methods — "the deployed app runs live" was checked against both the wiring code and the deployed `/healthz` header, and "scripts unchanged" against the saved originals by AST comparison rather than by reading the README.

VERDICT: PASS
