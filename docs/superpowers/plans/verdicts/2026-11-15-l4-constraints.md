# Verdict: l4-constraints (gh-16 follow-up, PR #32)

- **Reviewed:** branch `jay/gh-16-l4-constraints`, head `7583d85`, base `origin/main` = `2244225`, worktree `/Users/jay/Projects/receipts/.worktrees/l4c`.
- **Judge:** blind, fresh context. Read-only apart from running tests. The Neon integration run was done once.

## Rubric results

| Item | Result | Evidence |
|---|---|---|
| 1 Scope | Met | `git diff --name-only origin/main...HEAD` returned only `tests/test_db_constraints.py` (exit 0) |
| 2 Schema coverage | Met, with LOW #2 and #3 | See the constraint table below |
| 3 Forbidden row, then IntegrityError, then count 0 | Met | `tests/test_db_constraints.py:72-76` (`pytest.raises(IntegrityError)` around `engine.begin()`, then `_count == 0` on a new connection). The PK test (`:79-90`) asserts count 1 after the rejected duplicate (`:86`), deletes in `finally` (`:87-89`) and asserts 0 (`:90`). Ids come from `uuid4` (`:50-51`). |
| 3 JSON NULL | Met | `:96` uses `null()`, and its comment says why. In-memory SQLite check: a bare `None` was accepted and stored as `null` (JSON); `null()` was rejected with `IntegrityError` (command exit 0, no Neon access). |
| 4 Marking and skip | Met | `:29` sets `pytestmark = pytest.mark.integration`. `env -u DATABASE_URL uv run pytest tests/test_db_constraints.py -q -m integration -rs` gave 6 skipped, exit 0, reason `DATABASE_URL not set: runs-table constraint tests (test_db_constraints) skipped` (`:39-41`). `bin/jig:43-44` and `.github/workflows/ci-python.yml:19` both pass `-m "not integration"`. `--collect-only -m "not integration"` gave 145/152 collected, 7 deselected, which matches the PR's "deselected 1 -> 7". |
| 5 Neon run | Met | The given command gave `6 passed in 4.11s`, exit 0. Afterwards, `SELECT count(*) FROM runs WHERE id LIKE 'constraint-test-%'` = **0** and `SELECT count(*) FROM runs` = **1** (total rows in the `DATABASE_URL` database; content not read), snippet exit 0. |
| 6 Types and gates | Met | `uv run pyright` gave 0 errors, exit 0. `uv lock --check` exit 0. `grep -nE "Any\|type: ignore\|pyright: ignore\|noqa" tests/test_db_constraints.py` exit 1 (no matches). Check runs on `7583d85`: all 5 checks required by ruleset `27284472` passed (gitleaks, leak-gate, dependency-audit, ci-python, api-image). The third-party check `Mermaid Diagram Sync Assistant` was skipped and is not counted. PR title starts `gh-16:`. Red-first evidence is named, but MEDIUM #1 applies. |
| Security floor | Met | No secrets or URL in the file. No gate, ignore entry or test removed (one-file diff). |

### Constraint inventory (`src/receipts/db/schema.py`)

| Column | Constraint | Line | Tested |
|---|---|---|---|
| `id` | PRIMARY KEY (uniqueness) | 52 | Yes, `test_duplicate_primary_key_is_rejected` (`:79`) |
| `id` | NOT NULL, implied by the PK (Postgres marks PK columns NOT NULL; SQLAlchemy sets `nullable=False` for `primary_key=True`) | 52 | No (LOW #2) |
| `created_at` | NOT NULL | 53 | Yes (`:93`). `index=True` is an index, not a constraint. |
| `subject` | NOT NULL | 54 | Yes (`:93`) |
| `rival` | NOT NULL | 55 | Yes (`:93`) |
| `category` | nullable (`nullable=True`) | 56 | Correctly untested |
| `status` | NOT NULL; no CHECK on its values | 57 | Yes (`:93`). The file adds no CHECK. |
| `battlecard` | nullable (`nullable=True`) | 58 | Correctly untested |
| `events` | NOT NULL (`default=list` is client-side) | 59 | Yes (`:93`, via `null()`) |
| all string columns | `varchar(n)` length (64/200/16) | 52-57 | No (LOW #3) |

The schema has no CHECK, UNIQUE (other than the PK) or FK, and no test invents one.

## Findings

| # | Severity | Finding | Citation (`file:line` or command + exit) | Fix |
|---|---|---|---|---|
| 1 | MEDIUM | `test_duplicate_primary_key_is_rejected` was never seen failing for the right reason. The only red that covers it is the collection-time `NameError: Engine`, which tells you nothing about the assertion. The sabotage report says "5 failed ... 1 passed"; the 1 that passed is this test. Reading the test, it would fail without the PK (the second insert would succeed and produce `DID NOT RAISE`), but there is no observed evidence of that. | `tests/test_db_constraints.py:79-86`. PR #32 body via `gh pr view 32` (exit 0): "Sabotage (valid row instead of NULL) -> 5 failed `DID NOT RAISE IntegrityError`, 1 passed". `AGENTS.md:46-47` ("watch it fail for the right reason"; "Sabotage each guard separately") | Sabotage `:85` to insert `_valid(_new_id())`, delete that row too, watch `DID NOT RAISE`, revert, and name the run in the PR body |
| 2 | LOW | The PK's implied NOT NULL on `id` is not proven. The parametrize list leaves out `id`, and `_assert_rejected` keys its count on `str(values["id"])`, so a NULL-id case would need its own count. The real-world impact is small because Postgres cannot have a nullable PK column. | `tests/test_db_constraints.py:73,93`. `src/receipts/db/schema.py:52` | Add a NULL-`id` case that asserts `IntegrityError` and that the row count is unchanged |
| 3 | LOW | The docstring says PK and NOT NULL "are the constraints proven", but the `varchar(n)` limits are enforced only on Postgres (not SQLite) and are untested. They fall outside spec:48's list (NOT NULL, FK, CHECK, unique), so this is not a breach. Postgres would raise `DataError`, not `IntegrityError`. | `tests/test_db_constraints.py:7-8`. `src/receipts/db/schema.py:52-57`. `docs/superpowers/specs/2026-11-14-receipts-design.md:48` | Either state in the docstring that length limits are out of scope, or add an over-length test that asserts `DataError` |
| 4 | LOW | The tests run against `DATABASE_URL`, which here is the Render/demo database (1 row). The spec says the Neon `dev` branch. The PK test writes a valid `status="running"` row between `:83` and `:89`; a process killed in that window would leave a `constraint-test-*` row in the table that backs public History. The coordinator accepted this target, and the measured leftover count is 0. | `tests/test_db_constraints.py:37,82-89`. `docs/superpowers/specs/2026-11-14-receipts-design.md:46,48,50`. Leftover query = 0, total = 1 (exit 0) | Point the run at a `dev`-branch URL, or record the accepted deviation at spec:48 |
| 5 | LOW | The PR body does not follow the template. It has `## What` and `## Why` where the template has `## What and why`, has no `## Ticket` heading, writes evidence as bullets instead of the template checkboxes, paraphrases the `bin/jig` result instead of pasting its summary line, and has no `/judge` verdict attached yet. | `.github/PULL_REQUEST_TEMPLATE.md:1-9`. `gh pr view 32 --json body` (exit 0) | Reshape the body to the template, paste the jig summary line, and link this verdict |

No CRITICAL or HIGH findings.

## Worktree

`git -C /Users/jay/Projects/receipts/.worktrees/l4c status --short` returned nothing (exit 0), so no tracked or untracked changes. The ignored `__pycache__`/`.pytest_cache` directories are dated 20:41-20:42, before this review.

## Verdict

The brief's rule is that PASS needs zero HIGH and every MEDIUM resolved or accepted with a reason. MEDIUM #1 is open, so this is FAIL. It becomes PASS once #1 is resolved (one sabotage run named in the PR) or the coordinator accepts it with a reason. LOW #2-#5 do not block.

VERDICT: FAIL

Practice applied: Sabotage each guard separately (AGENTS.md section 4). The one sabotage reported turned the five NULL cases red but left the duplicate-PK test green, so that test has only ever been seen passing.
