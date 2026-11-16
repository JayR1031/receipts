# Judge verdict: `l6-license-followup` (issue #18, PR #23)

- **Head reviewed:** `e2346318279ff1399b4c2abcab023abc6b982fd8`. It matches `gh pr view 23 --json headRefOid` (exit 0), `origin/jay/gh-18-l6-license-followup` after `git fetch origin` (exit 0), and the worktree `.worktrees/l6-followup` HEAD (clean `git status --short`).
- **Base:** `origin/main` = `6628208`. One commit on the branch: `e234631`.
- **Reviewed against:** `docs/superpowers/plans/verdicts/2026-11-14-l6-license.md` (findings 1, 2, 4, 8) and `docs/superpowers/plans/verdicts/2026-11-14-l6-license-a5e3edf.md` (LOW-3, LOW-5).
- **Not run:** `bin/jig`, because this review was read-only. `ci-python` succeeded on `e234631`, and the diff contains no code.
- **Judge:** blind, fresh context, 2026-11-14. The only file I created is this one. The vendor pages were downloaded to the session scratchpad.

## Evidence

| Command | Exit | Result |
|---|---|---|
| `git diff --stat origin/main...origin/jay/gh-18-l6-license-followup` | 0 | 1 file, `docs/adr/0005-app-architecture-and-hosting.md`, 1 insertion, 1 deletion |
| `git diff -U0 … \| grep '^@@'` | 0 | One hunk only: `@@ -22 +22 @@` |
| `diff` of ADR lines 1-21, `origin/main` vs head | 0 | Header unchanged |
| `curl -sL https://ui.aceternity.com/pricing` | 0 | HTTP 200, 217,727 bytes. "The only restriction is that you cannot resell or redistribute the components themselves as a competing template or component library" occurs 1 time. It is in the FAQPage JSON-LD answer to "Can I use Aceternity UI components in commercial projects?". The server-rendered accordion shows the question without its answer. |
| `curl -sL https://ui.aceternity.com/terms` | 0 | HTTP 200, 73,830 bytes. Stripped text reads "License Unless otherwise stated, Aceternity Solutions Private Limited … own the intellectual property rights …". The phrase opens the License section. |
| `curl -sL https://ui.aceternity.com/licence` | 0 | HTTP 200, 72,738 bytes. "each item available for purchase or download on ui.aceternity.com" occurs 1 time, in the Overview scope sentence. The 5 original clauses each occur 1 time, and "Aceternity License" occurs 2 times. |
| `python3 -I` count of `<li>` items between "Free plan includes" and "1-Year License" on `/pricing` | 0 | 6 items: free components, MCP access, copy and paste, Next.js/React/Tailwind/Framer Motion, responsive, documentation. 0 of the 6 mention `template`. |
| `grep -cF` on head ADR line 22 for 15 retained strings | 0 | 15 of 15 present: licence name, the `/licence` URL with read date, the product URL, the 5 clauses, "has no attribution clause", "verdict **permitted**", the dated owner confirmation, the All-Access sentence, `0f6acc1`, the 404 fact, and the no-LICENSE fact |
| `grep -cEw 'he\|him\|his'` on head ADR line 22 | 1 | 0 matches |
| `wc -w` on ADR line 22 | 0 | 223 words on `origin/main`, 299 at head |
| `gh pr checks 23` | 0 | api-image, ci-python, dependency-audit, gitleaks and leak-gate all `pass`. "Mermaid Diagram Sync Assistant" is `skipping`. It is a third-party check, not required, and not counted. Nothing was pending, so no polling was needed. |
| `gh api repos/JayR1031/receipts/rules/branches/main` | 0 | 5 required checks: gitleaks, leak-gate, dependency-audit, ci-python, api-image |
| `gh api …/commits/e234631…/check-runs` | 0 | The 5 required runs show `success` at `head_sha` `e234631` |

## Rubric results

1. **Scope: met.** One file and one line (ADR:22). Header unchanged.
2. **Quotes: met.** 3 of 3 new quotations are verbatim on the live pages (evidence rows 4-6). No misquote.
3. **Free-plan count: met.** "lists six items, none of them templates" matches 6 items with 0 template mentions.
4. **Findings addressed:**
   - **Finding 1 and LOW-5: met.** The bullet now says "That is our reading of the clause …". It records the FAQ's narrower wording and adds "we keep the stricter reading".
   - **Finding 2: met, with LOW-4.** "only licence text" became "only item licence text", and the `/terms` sentence was added.
   - **Finding 4 and LOW-3: met.**
   - **Finding 8: met.** The scope sentence is quoted.
   - **Nothing lost:** 15 of 15 retained strings are present, and no gendered pronoun appears. One retained clause lost its source attribution (LOW-3).
5. **Gates: met.** 5 of 5 required checks pass on `e234631`. The skipping third-party check is named above and not counted.
6. **PR hygiene: met, with LOW-1, LOW-2 and LOW-5.**
   - The title starts `gh-18:`.
   - The `/judge` box is unchecked, which is correct.
   - Findings 5 and 6 are named as open. Finding 9 is not named (LOW-2).

- **Tests / watched failing:** not applicable. The change is docs-only, and the body says "none; docs-only".
- **Typed boundaries:** not applicable.
- **Security floor:** no secrets and no real data. No workflow, ignore file or test was touched.
- **Record hygiene:** no title or heading is contradicted.

## Findings

| # | Severity | Finding | Citation (`file:line` or command + exit) | Fix |
|---|---|---|---|---|
| 1 | LOW | The PR body says "Not addressed here: findings 5 (tier name), 6 (commands) and a5e3edf LOW-5 are left as they were". The diff does address LOW-5: it adds the "reading" label that LOW-5 asked for, and the body's own first bullet says so for finding 1. The body contradicts the diff. | `gh pr view 23 --json body` (exit 0), "What and why", last bullet. `git diff --word-diff=plain origin/main...origin/jay/gh-18-l6-license-followup` (exit 0): `{+repository). That is our reading of+}` at `docs/adr/0005-app-architecture-and-hosting.md:22` | Remove "and a5e3edf LOW-5" from the "Not addressed" bullet, and mark LOW-5 as covered by finding 1. |
| 2 | LOW | The body's list of open LOWs omits finding 9 (a5e3edf LOW-4). ADR:22 still gives who and when but not where: "the repository owner confirmed on 2026-11-14 that they hold an All-Access licence". Finding 7 (length) is also unnamed, and the line grew from 223 to 299 words. | `gh pr view 23 --json body` (exit 0). `docs/adr/0005-app-architecture-and-hosting.md:22`. `wc -w` on line 22 at base and head (exit 0) | Add finding 9 and finding 7 to "Not addressed here", or name the channel of the confirmation. |
| 3 | LOW | The edit replaced "because the same page says" with "That is our reading of the clause". The bullet no longer says which page the clause comes from. The nearest URL before it is `/pricing`, where the clause has 0 matches. The clause is on `/licence`, with 1 match. | `docs/adr/0005-app-architecture-and-hosting.md:22`. Word-diff above: `[-same page says-]{+clause+}`. `python3 -I` count on the fetched pages (exit 0): pricing 0, licence 1 | Write "our reading of the licence page's clause". |
| 4 | LOW | The `/terms` sentence records only the opening phrase and the conclusion ("so the item licence above governs the template"). It does not say what the section would otherwise restrict: "You may access this from ui.aceternity.com for your own personal use … You must not: Republish material …". Unlike the repository condition, this conclusion is not marked as a reading. The reasoning is sound, and finding 2's core point (explain why `/licence` governs) is met. | `docs/adr/0005-app-architecture-and-hosting.md:22`. `curl -sL https://ui.aceternity.com/terms` (exit 0), License section text | Optionally add "which otherwise limits site material to personal use", and "(our reading)". |
| 5 | LOW | The body's Evidence line "`bin/jig` green … exit 0" does not name the commit or tree it ran on. The previous round flagged a jig line tied to the wrong SHA (a5e3edf verdict LOW-1). `ci-python` succeeded on `e234631`, which covers the same four classes. | `gh pr view 23 --json body` (exit 0), Evidence box 1. `gh api …/commits/e234631…/check-runs` (exit 0) | State "on `e234631`", or cite the `ci-python` run 43654050895. |

HIGH: 0. MEDIUM: 0. LOW: 5.

VERDICT: PASS

Practice applied: a quote is verified at the source, not from the report. I fetched `/pricing`, `/terms` and `/licence` myself, confirmed all 3 new quotes verbatim, and counted the 6 Free-plan items. This showed that the FAQ quote is only in the page's JSON-LD, and that the edit dropped the clause's source page. Neither is visible from the diff alone.
