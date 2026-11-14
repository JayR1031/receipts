# Receipts — instructions for AI agents

Read this file first. It is the engineering standard for this repository. Sections 0 to 8
come from the `agentic-standard` kit and are updated by pulling the kit; section 9 is this
project's own and is the only section edited here.

## 0. Rule Zero: verify before you claim

- Before stating anything about this repo, ask **which artifact answered, from which revision**: a file at a commit, a command's exit code and output, a test run you watched. Memory of a previous session is not an artifact.
- **A number carries its set and its denominator.** "Nine of eleven accuracy tests, on the held-out set" is a claim. "Ninety percent accuracy" is not.
- **A gate's status is read from the workflow file**, not from a doc that describes it. `grep -n exit-code .github/workflows/*.yml` takes a second and does not age.
- **When a claim is disproved, fix the top of the record.** Edit the title, the heading, the first line. A correction in a comment underneath is a footnote, and people and agents read titles.
- **When a metric reads perfect, find the bucket nothing asserts on.** A round number is more often a broken instrument than a finished job.
- **Investigations add four checks** — logs, traffic, incidents, audits, anything where the evidence is data rather than code:
  - **A negative claim states its search scope.** "Not found" names every place searched: all branches, monorepo paths, and the record of **what is deployed**. Start from the deployment's commit, then the repositories; a name search finds what was named, not what runs. Without the scope it is "not found where I looked", and says so.
  - **Attribution needs a baseline.** A signal blamed on an actor must be absent, or different, in a normal window and in known-good traffic. One shared signal (a fingerprint, a network, a user agent) attributes nothing.
  - **A verdict needs two independent methods.** "Got in", "got the data", "is safe" need two kinds of evidence to agree: traffic and code, logs and the database. Until they agree the status is **pending**, said in that word, and no provisional verdict goes out.
  - **Every measurement is a saved query** with its expected result, including the known false positives it must exclude, so the next pass re-runs it instead of re-deriving it.

## 1. The loop

Agent output is probabilistic. The formatter, linter, type checker and tests are the deterministic gauge, and code moves forward only when the gauge says so. Diagram: [the jig loop](https://JayR1031.github.io/agentic-standard/atlas/03-jig-loop/).

- Every change runs `bin/jig` before it is called done. The jig stops at the first failing class (format, lint, types, tests) so the next attempt sees one problem at a time.
- **Three repair attempts.** Feed the exact stderr into the next attempt. On the third failure, stop, and escalate to a human with the full trace and what was tried. Never widen a rule, delete a test, or add an ignore to get to green.
- Wipe bytecode caches before every run. A same-size edit in the same second can leave a stale `.pyc` in place and every later result in that sweep is invalid.

## 2. Plan the work, then isolate it

- Before any implementation, the ask goes through `/improve-prompt` and becomes a brief in `docs/superpowers/briefs/`. The orchestrator (`/orchestrate`) turns the brief into a task graph in `docs/superpowers/plans/` and shows it before dispatching anything.
- **Parallel only when file scopes are disjoint and there is no shared mutable state.** A task that needs a contract first (a schema, an API shape, a shared type) is sequential behind the task that produces the contract.
- One ticket, one branch, one worktree, one agent. Branch `<user>/<ticket-key>-<slug>`. Each task names the files it may touch; touching anything else is a defect.
- Small PRs. One approval click per PR; changing a PR's base discards approvals, so rebase with `git rebase --onto` and ask for the re-click once.
- Full text: [orchestration patterns](https://JayR1031.github.io/agentic-standard/guides/orchestration-patterns/).

## 3. Architecture agents can hold

- Functions under 60 lines and cyclomatic complexity under 7, or decompose into pure helpers. An agent reasons reliably about code it can hold in one view; long functions are where hallucinated parameters hide.
- **Typed boundaries.** No `dict[str, Any]` or `any` across module lines. Domain entities are dataclasses, Pydantic models, or TypeScript types, so a wrong field name fails under `pyright` or `tsc` before runtime.
- **Business rules are pure.** Immutable input in, structured result out, no database reads, no network, no clock. I/O lives at the edges and is injected.
- Comments explain *why*; the code already says what. Docs that describe a contract change in the same PR as the contract.
- Full text: [coding conventions](https://JayR1031.github.io/agentic-standard/guides/coding-conventions/).

## 4. Testing

- TDD. Write the failing test, **watch it fail for the right reason**, then implement. A test that stays green when you break the thing it claims to cover is worse than no test, because it reads as coverage.
- **Sabotage each guard separately.** Inject the defect, confirm red, remove it, confirm green. A guard can be shadowed by another that runs first; if a sabotage turns nothing red, ask whether the path reaches it.
- For schema and SQL changes, **behaviour against a real database is the only evidence.** Catalogue checks (column exists, constraint present) pass while the exact row they exist to stop goes through. A `CHECK` that evaluates to `NULL` passes; use `IS NOT DISTINCT FROM`.
- Run the file alone as well as the whole suite; collection order can hide or reveal a failure.
- **A skipped test is not a passing test.** Report skips by name, with the reason.
- Full text: [testing standard](https://JayR1031.github.io/agentic-standard/guides/testing-standard/).

## 5. Blind judge

- The agent that wrote the code does not review it. `/judge` runs a fresh-context reviewer with the ticket, `git diff origin/main...HEAD`, and the rubric.
- **Every objection cites `file:line` or a command exit trace.** "Looks fragile" is not a verdict and is dropped.
- The judge's verdict, not the implementer's "done", is what unblocks a dependent task.
- **Claims get a blind judge too.** Before findings, a report or any analysis leaves the repo (tracker, email, PR description), `/verify-claims` runs a fresh-context `claims-judge` on the draft and its evidence. A FAIL blocks sending; the draft is fixed, not the verdict.
- Diagram: [orchestration, from brief to merge](https://JayR1031.github.io/agentic-standard/atlas/05-orchestration/).

## 6. Security floor

- Secrets live in the environment (`~/.zshenv` or a secret manager). Config carries **references** (`${NAME}`), never values. A leaked secret is rotated, not deleted from history.
- **Gitleaks blocks** (`--exit-code 1`) over the full history on every PR. Known-safe findings are pinned by fingerprint in `.gitleaksignore`, each with a one-line justification.
- **Data denylist gate** (`scripts/leak_gate/`) runs repo-wide with no path filter. Its contents are this project's business (section 9). An empty denylist is a gate that is green about everything; `bin/red-test` proves the gate can fail.
- Dependency audit blocks on high and critical. Dependabot is on. Workflow `permissions:` are least-privilege and every action is pinned to a commit SHA.
- Never commit real client or personal data. When in doubt, it does not go in the repo.
- Full text: [security baseline](https://JayR1031.github.io/agentic-standard/guides/security-baseline/). The threat-model template: `docs/security/`.

## 7. Writing

- Plain language for risk and consequences; exact terms for the technical claim, defined in plain words on first use. **Jargon is explained, not deleted.**
- Say who said what and where; do not refer to things only by ticket id.
- Code, identifiers and code comments are in English. Document languages are a section 9 decision.

## 8. Commands

Canonical commands for this repository. Agents run these and nothing else for the same purpose.

```bash
uv sync                          # install (python) — see section 9 for typescript projects: pnpm install
bin/jig                          # format check, lint, types, unit tests — stops at first failing class
bin/jig --fix                    # apply formatter and safe lint fixes first
bin/jig --scope all              # adds integration tests
bin/red-test                     # prove every installed gate can fail (plant, red, remove, green)
bin/plan-check docs/superpowers/plans/<plan>.md   # validate an orchestrator task graph
```

## 9. Project overlay

*The only section this project edits.* Stack: `python` · Cloud: `none` (ADR-0001) · Tracker: `github` (ADR-0002) · Approved AI vendors: anthropic, openai (ADR-0004).

Add here, and only here: who approves PRs, document languages, data classifications and what belongs in `scripts/leak_gate/denylist.txt`, tenant or customer conventions, communication channels, and anything else that is true of this organization and not of software in general.

- **Design spec:** `docs/superpowers/specs/2026-11-14-receipts-design.md`. Architecture and hosting: ADR-0005. Third parties: ADR-0004.
- **Who approves PRs:** the repository owner (`JayR1031`), after a `/judge` verdict.
- **Lanes (all builders: Claude Code, Codex, Mel).** Touch only your lane's folder (`harness/`, `verify/`, `packs/`, `db/` + `api/`, `ui/`). `src/receipts/contracts.py` and dependencies are frozen after Wave 0; a lane that needs either changed stops and asks instead of editing them. Tests use the in-memory fakes from Wave 0; no network in unit tests.
- **Document language:** English.
- **Data:** runs contain public web content only. No user accounts, no personal data, no real API keys in fixtures.
