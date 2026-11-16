> Saved by the main session from the read-only judge's report (round 1).

# Judge verdict: w3-records (PR #51)

- **What was reviewed:**
  - `git diff origin/main...HEAD` in `/Users/jay/Projects/receipts/.worktrees/w3-records`. The head is `20fab2a`; the base and merge-base are `a9eeb61`.
  - The PR body (`gh pr view 51`, exit 0).
- **Rubric 2–4 (tests, watched failing, typed boundaries):** not applicable. The diff adds 52 Markdown files and no code. The PR body says "Tests. None: records only."

## Findings

| # | Severity | Finding | Citation | Fix |
|---|---|---|---|---|
| 1 | HIGH | **A real email address appears in full.** It is the Mellea package's ibm.com contact address, quoted from the `mellea-0.9.0` package metadata.<br>• The ticket says no real email address may appear.<br>• It is a public organisational contact, not a person's address, so the harm is small. The rule makes no exception for it, though.<br>• Another file in this PR already masks the same address as "author email @ibm.com". | `docs/superpowers/plans/verdicts/2026-11-15-w3-readme-posts-claims.md:54`, from my own scan (`python3 -I <scratchpad>/scan.py`, exit 0, kind `email`).<br>The other 10 email-shaped matches are npm `package@version` strings: `briefs/W3-ship.md:21,41`, `verdicts/2026-11-14-l6-landing.md:33`, `2026-11-15-gh37.md:5,30,39,40` (2 matches), `2026-11-15-gh37-r2.md:15` and `2026-11-15-gh42.md:50`.<br>The masked version: `verdicts/2026-11-15-gh39-body-claims.md:48`. | Replace the address with "an ibm.com contact address", as `gh39-body-claims.md:48` does. Or record that the owner explicitly approved publishing it. |
| 2 | MEDIUM | **The PR body's scan claim is wrong and cannot be re-run.** It says: "A scan for secret-shaped strings, email addresses, and Codex session details found nothing to remove. The only hits were a placeholder DSN, `~/.zshenv` name counts and two 'not read' notes."<br>• Any email scan finds the address in finding 1.<br>• The body gives no command and no exit code for the scan. | `gh pr view 51 --json body`, exit 0, "Privacy" bullet 3. The contradicting line is the one in finding 1. | Name the scan command and its exit code. List what it found, including the address or its removal. |
| 3 | MEDIUM | **"The finding itself and its fix are unchanged" has no evidence.** This is the PR body's claim about the redacted round-3 file.<br>• The body cites no copy of the file from before the redaction, and no diff.<br>• No such copy can be found: git history holds only the redacted version, and the main checkout's copy is byte-identical to it. | `gh pr view 51`, exit 0, "Privacy" bullet 1.<br>`git log --all --oneline -- docs/superpowers/plans/verdicts/2026-11-15-w3-readme-posts-claims-r3.md`, exit 0: only `20fab2a`.<br>`cmp` of the 52 PR files against the copies in `/Users/jay/Projects/receipts/docs/superpowers/`: 0 of 52 differ. | Say how this was checked. For example, give the line numbers a local diff changed (no text), all in the header and in finding 2's evidence cell. Or attribute it: "owner-approved redaction; the Severity and Fix cells were not edited". |

## Checked, no finding

- **Scope (rubric 1):**
  - `git diff --name-status origin/main...HEAD` (exit 0): all 52 paths are new `.md` files. 4 are in `docs/superpowers/briefs/` and 48 in `docs/superpowers/plans/verdicts/`.
  - Filtering out the two allowed folders leaves no path (grep exit 1).
  - The #41 brief is not in the diff. It is committed on the local branches `jay/gh-41-google-sign-in` and `jay/gh-41-contract` (`git ls-tree`, 1 match each). No #41 PR is open yet; the open PRs are #49 and #51.
- **Gates (rubric 5):**
  - `git diff --quiet origin/main...HEAD -- .github .gitleaksignore scripts bin`: exit 0, so no gate file changed.
  - `.github/workflows/security.yml:22` still runs gitleaks with `--exit-code 1`.
  - No file is deleted.
- **Leak gate:** `python3 -I scripts/leak_gate/check_tracked.py` exits 0 ("scanned 182 files against 2 patterns"). Its 2 denylist patterns match 0 lines in the 52 files.
- **Gitleaks, run locally:**
  - `gitleaks dir docs/superpowers --redact --exit-code 1`: exit 0.
  - `gitleaks git . --log-opts=origin/main..HEAD --redact --exit-code 1`: exit 0.
- **CI:** `gh pr checks 51` exits 0. All 5 checks pass: api-image, ci-python, dependency-audit, gitleaks and leak-gate. An earlier call exited 8 with 3 still pending.
- **Own scan** (`scan.py`, exit 0, over the 52 files at `20fab2a`):
  - **Patterns with 0 hits:**
    - key shapes for Anthropic, OpenAI, ElevenLabs, GitHub, AWS, Google, Slack, Hugging Face and Render;
    - JWTs and private-key headers;
    - DSNs with credentials, and Neon hosts;
    - `secret|token|password = value` assignments and bearer tokens;
    - phone numbers (2 patterns);
    - latitude/longitude pairs.
  - **GPS:** mentioned only as present or as a distance, never as coordinates (`2026-11-15-w3-readme-posts-claims.md:88`, `-r2.md:40,60-63`, `-r3.md:106`).
  - **26 `NAME=value` hits, none secret:** public URLs, sqlite DSNs, cache paths, `GIT_SHA` test values and one fake `not-a-…` key (`gh39-body-claims.md:38`).
  - **9 high-entropy hits, none credentials:** ElevenLabs agent and test ids and a Vercel deployment id (`gh37.md:6`, `gh42.md:6-7`).
  - **`.zshenv`:** 11 lines, with setting names and counts only (for example `gh41-issue-edit-claims.md:22,90`).
- **Codex details:**
  - All 22 matches of my Codex-detail patterns are in the claims rounds 3–5. None gives a Codex session id, time, folder, file name or setting.
  - Round 3 is redacted (`-r3.md:1,9,128`).
  - `-r4.md:126` and `-r5.md:13,65` mention the withheld setting without describing it.
  - `~/.codex` and `~/Documents/Codex` appear only in the "not read" notes at `-r4.md:33` and `-r5.md:48`.
- **PR body counts and records:**
  - 52 files = 4 briefs + 48 verdicts.
  - The W0/W1 and W2 briefs are already on `origin/main` (`git ls-tree`).
  - All 48 untracked verdict files in the main checkout are in the PR (`comm` finds no difference either way).
  - The session transcript has owner records at 2026-11-15T19:09:30.372Z (the redaction answer) and 2026-11-16T01:01:15.879Z ("Publish as-is").
  - Issues #12, #13, #17, #18 and #19 are closed. Each has a comment citing a merged PR: #22, #28, #26, #21/#23 and #29 (`gh issue view` and `gh pr view`, exit 0).

## Outside the rubric (not a finding)

- None of these is on the ticket's list, and the owner chose to publish the files unchanged. They are listed so that choice is informed:
  - the owner's full name as a git author (`gh40-body-claims.md:11`);
  - local home paths and Claude Code session ids (`gh41-issue-edit-claims.md:78-80`, and 49 lines in all with session ids);
  - quoted owner messages (`-r5.md:28-30`, `gh41-issue-edit-claims.md:93`);
  - the event photo's camera model and capture time from its EXIF data (`2026-11-15-w3-readme-posts-claims.md:88`).
- The PR body says the verdicts are published "as the reviewers wrote them". That is not true of round 3, but the next section of the body discloses the redaction.

VERDICT: FAIL
