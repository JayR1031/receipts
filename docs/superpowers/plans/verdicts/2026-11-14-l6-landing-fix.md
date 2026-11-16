# Judge verdict: `l6-landing-fix` (issue #18)

- Work under review: `/Users/jay/Projects/receipts-landing` @ `d8179a3` (parent `0f7d0ce`), branch `main`, local only.
- Reference: prior verdict `docs/superpowers/plans/verdicts/2026-11-14-l6-landing.md` (FAIL at `0f7d0ce`); plan `docs/superpowers/plans/2026-11-14-w0-foundations-and-w1-lanes.md` "Scope cut 2026-11-14" (`:20-38`; the plan is untracked and was edited while I reviewed it, so plan line numbers are as of my last read, re-resolved with `grep -n`); spec `docs/superpowers/specs/2026-11-14-receipts-design.md` (`:33`, `:35`, `:39`, `:41`, `:43`).
- Judge: blind, fresh context, 2026-11-14. Neither repository was modified. What I did write: `pnpm build` ran 5 times and rewrote the git-ignored `.next/`. The last build ran with `NEXT_PUBLIC_APP_URL` unset, so `.next/` now matches a default build. I extracted the template zip into my session scratchpad and only ran `cmp`/`diff` on it, with no code run from it. I wrote this file. Every build ran with `NEXT_TELEMETRY_DISABLED=1`.

## Gate evidence

| Command | Exit | Result |
|---|---|---|
| `NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_APP_URL= pnpm --dir /Users/jay/Projects/receipts-landing build` | **0** (was 1 at `0f7d0ce`) | Compiled; 4 of 4 static pages; routes `/`, `/_not-found`. `grep -o 'href="#"' .next/server/app/index.html \| wc -l` = 5 |
| `env -u NEXT_PUBLIC_APP_URL NEXT_TELEMETRY_DISABLED=1 pnpm --dir … build` | 0 | 4 of 4 static pages; 5 × `href="#"` |
| `NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_APP_URL=https://example.invalid pnpm --dir … build` | 0 | `grep -c 'href="https://example.invalid"' .next/server/app/index.html` = **2** (exit 0). `grep -c` counts lines, not matches: `grep -o … \| wc -l` = **3** occurrences on those 2 lines, which matches the prior verdict's 3. 2 × `href="#"` remain (the GitHub links, `lib/site.ts:13`) |
| `NEXT_PUBLIC_APP_URL="   "` (whitespace only) `… build` | 0 | 5 × `href="#"`, so `.trim()` covers this case too |
| `pnpm --dir /Users/jay/Projects/receipts-landing lint` | 0 | `eslint .`, no output |
| `env -u NEXT_PUBLIC_APP_URL … build` (final, restores `.next/` to the default) | 0 | Used for the copy greps below |
| `grep -o -i 'four[^<]\{0,30\}' .next/server/app/index.html` | 1 | 0 hits (was 3 × "Four domain specialists") |
| `grep -o -i -E 'news\|social\|changelog\|product ' .next/server/app/index.html` | 1 | 0 hits for the cut domains |
| `grep -rn -i -E 'four\|news\|social\|product\|model call\|haiku\|5th\|fifth' app components lib README.md LICENSE-TEMPLATE.md` (`*.ts`, `*.tsx`, `*.md`) | 1 | 0 hits in source |

## Rubric 1: prior findings at `d8179a3`

| Prior # | Status | Evidence |
|---|---|---|
| 1 (HIGH) four specialists | **Fixed** | `components/hero.tsx:67-69` "Two domain specialists today (pricing, and positioning and SEO) … each is a YAML pack, so more domains can be added"; `components/features.tsx:39` "Watch the specialists"; `:51` "Two ship today: pricing, and positioning and SEO"; `:79` "Domain specialists gather claims"; `lib/site.ts:27` "Domain specialists (pricing, and positioning and SEO today)". Rendered meta description matches. Illustration rows `components/receipt-preview.tsx:23,30,37,44` name only `Pricing` and `Positioning / SEO`. One unverified row remains (`:44-48`). The prior fix note still applies: L3 is `planned` (plan `:291`), so "today" (`hero.tsx:68`, `features.tsx:51`) states the scope cut, not what is built. Recheck after L3 merges. |
| 2 (HIGH) empty app URL breaks the build | **Fixed** | `lib/site.ts:10` `(process.env.NEXT_PUBLIC_APP_URL ?? "").trim() \|\| "#"`. The empty value gives exit 0 (table above). Unset, whitespace and real URL all exit 0. `.env.example:1-3` and `README.md:17-19` now describe what actually happens. |
| 3 (MEDIUM) budget for model calls, run stops | **Fixed** | `components/features.tsx:57` "Each specialist has a search budget, a fetch budget and a timeout. When a budget is spent, the specialist reports what it has…". This matches spec `:33` (`max_searches`, `max_fetches`, `timeout_s` per pack) and the W0 contract `DomainPack` (`git show origin/jay/gh-12-w0-foundations:src/receipts/contracts.py`, lines 191-193). The copy no longer claims a model-call budget or a run-level stop. |
| 4 (MEDIUM) README "verified receipt" | **Fixed** | `README.md:3-4` "every claim carries a receipt and each is marked verified or not". |
| 8 (LOW) template file lists | **Fixed as specified** | `LICENSE-TEMPLATE.md:77-83`: `eslint.config.mjs` and `next.config.ts` have moved to the "rewritten" list, and the kept list is now labelled "unchanged". `cmp` against the extracted archive: 8 of 8 "unchanged" files are byte-identical (`button.tsx`, `ui/glowing-effect.tsx`, `lib/utils.ts`, `app/globals.css`, `app/favicon.ico`, `postcss.config.mjs`, `tsconfig.json`, `components.json`). All 7 "rewritten" files differ from the template. Residual gap: L4 below. |
| 9 (LOW) local path with account name | **Fixed at HEAD** | `LICENSE-TEMPLATE.md:4` now gives the file name only. `grep -rn '/Users' . --exclude-dir={node_modules,.next,.git}` exit 1. Residual in history: L5 below. |

The prior accepted items stay accepted, and the fix did not touch them. 5: there are still no test files (`git ls-files`, 25 paths, none a test). 6: `receipt-preview.tsx:59-68` is unchanged. 7: `features.tsx:45` is unchanged. 10: `README.md:8-13` is unchanged.

## Rubric 2: regressions

- `git diff 0f7d0ce d8179a3 --stat` shows exactly 6 files changed (21 insertions, 21 deletions): `LICENSE-TEMPLATE.md`, `README.md`, `components/features.tsx`, `components/hero.tsx`, `components/receipt-preview.tsx` and `lib/site.ts`. That is the allowed set.
- `git diff 0f7d0ce d8179a3 -- package.json pnpm-lock.yaml | wc -c` = 0, so no dependency changed.
- `pnpm lint` exit 0.
- `git remote -v | wc -l` = 0, and the only branch is `main`.
- No `.env`: `ls -a | grep '^\.env'` prints only `.env.example`, and `.env.example:3` holds a name with no value.
- `.vercel/` exists locally (`README.txt`, `project.json`), but `git ls-files .vercel | wc -l` = 0 and `git check-ignore -v .vercel` matches `.gitignore:26` (exit 0). `.gitignore` is not in the diff, so it was already ignored at `0f7d0ce`.
- `git status --short` was empty after all builds (exit 0) in the landing repo. In this repo it showed only the brief, the plan and `verdicts/` as untracked.

## Rubric 3: honest copy, sentence by sentence

- `hero.tsx:57`, `:67-71`: matches scope cut rows 2 and 5, and the future is framed as "more domains can be added". The quote-match wording is noted at L3.
- `features.tsx:27`, `:33`, `:79-80`: match spec `:9` and `:41`.
- `features.tsx:39`: see L1.
- `features.tsx:45`: prior item 7, still accepted.
- `features.tsx:51`: see L2.
- `features.tsx:57`: matches spec `:33`.
- `lib/site.ts:4-6`, `:25`, `:27`: match.
- `README.md:3-4`, `:17-19`, `:23-25`: match.
- Illustration: 4 rows (`receipt-preview.tsx:21-50`), 3 with `verified: true` and 1 with `verified: false`. The count is computed from the array (`:52`, `:67`), and the rendered HTML has `3<!-- --> of <!-- -->4`. The caption "Run summary (illustration, not live data)" is kept (`:60`) and rendered once. One row's content is inconsistent with its receipt type: L6.

## Findings

| # | Severity | Finding | Citation (`file:line` or command + exit) | Fix |
|---|---|---|---|---|
| M5 | MEDIUM (accepted, carried) | No test watched failing; the repo has no tests. **Accepted** for the prior verdict's reason: the L6 brief row defines the proof as a build exit 0 plus a render check, not TDD. The behaviour the fix changes (finding 2) was watched failing by the prior judge (exit 1) and now passes (exit 0). I ran both builds myself. | prior verdict finding 5; commit `d8179a3` message gives "build exits 0" with no command; plan `:297` records the orchestrator's exit codes; this verdict's gate table | None for this lane. |
| L1 | LOW | The card title "Live agent panel" and its three live signals (page being fetched, search being logged, claim being checked) use the pre-cut "live panel" wording. Scope cut row 5 moved that to the "Was" column; "Now" is "live progress", and L5 is not built. This is the same class as accepted item 7. | `components/features.tsx:37-39`; plan `:30`; plan `:293` (`l5` planned) | Recheck against L5's merged UI before any public redeploy, as for item 7. If L5 does not show those signals, use "Live progress" and describe only what it shows. |
| L2 | LOW | "adding a domain means adding a file" holds only for the two cut domains. The frozen `Domain` literal keeps `news_social` and `product`, and `DomainPack.id` is typed `Domain`, so any other domain also needs an edit to W0's frozen `contracts.py`. The wording follows the prior judge's suggested text and spec `:33`, so this is clarity, not a breach. | `components/features.tsx:51`; `git show origin/jay/gh-12-w0-foundations:src/receipts/contracts.py` lines 15 and 183 (exit 0; W0 is PR #22, not merged, plan `:288`) | Optional: "so adding one of the planned domains means adding a file". |
| L3 | LOW | "verified only when its quote is found on the fetched page" reads as a verbatim match. The Verifier also accepts `rapidfuzz.partial_ratio ≥ 90` after normalisation, and scope cut row 4 keeps fuzzy matching. This predates the fix and was not raised before. | `components/hero.tsx:69-70`; `components/features.tsx:33`; `lib/site.ts:27`; spec `:41`; plan `:29` | Optional: "found (exactly, or as a near-verbatim match) on the fetched page". |
| L4 | LOW | The template-file record is still incomplete. `app/layout.tsx`, `app/page.tsx`, `package.json` and `.gitignore` exist in the template and were edited (template script and metadata removed, sections removed, 3 dependencies removed, ignore entries changed), but they appear in neither list. This predates the fix. | `LICENSE-TEMPLATE.md:77-83`; `cmp` of those 4 files against the extracted archive → differ; `diff` shows template-derived content (for example the template's `app/layout.tsx` has `import Script from "next/script"`, which the landing repo replaced at its line 7) | Add the 4 files to the "rewritten" list, or call it "including". |
| L5 | LOW | The local path removed for finding 9 is still in history. If the repo is ever pushed with its history, the account name is disclosed. The licence condition says the repo stays private (plan `:248`), which limits the consequence. | `git log --all --oneline -S'/Users/jay/Downloads'` exit 0 → `c65d707`, `d8179a3`; `git grep -n '/Users/' $(git rev-list --all) -- LICENSE-TEMPLATE.md` → `0f7d0ce:LICENSE-TEMPLATE.md:4`, `c65d707:LICENSE-TEMPLATE.md:4` | Before any push, decide whether to rewrite history (local only, no remote yet) or accept the disclosure. |
| L6 | LOW | This row was introduced by the fix. Its receipt type cannot evidence its claim. A logged search row is `SearchReceipt{query, rank, url, ts}`, which carries no page title, and `positioning_seo`'s search receipts are a brand's rank across category queries. So "The page title targets a comparison keyword" with "Search row logged this run" shows a receipt that proves something else. | `components/receipt-preview.tsx:37-41`; spec `:35`, `:39` | For example: claim "The rival ranks in the top 3 for a category query.", receipt "Search row logged this run." |
| L7 | LOW (accepted, carried) | Prior items 6, 7 and 10 are unchanged by this fix. | `components/receipt-preview.tsx:59-68`; `components/features.tsx:45`; `README.md:8-13` | As in the prior verdict. |

Outside this commit's scope, recorded so it is not lost: plan `:250-262` records a production Vercel deployment made at 23:27 UTC. That is before `d8179a3` was committed (23:30 UTC), and the plan says the live page then read "four domain specialists". Redeploying or removing it is the OPEN user decision there, and this commit cannot change it. I did not run `vercel` or `curl`, so I have not verified what that deployment serves now.

VERDICT: PASS

Zero HIGH and zero new MEDIUM. All 6 of the 6 findings `d8179a3` claims to fix (1, 2, 3, 4, 8, 9) are fixed. The one MEDIUM (carried 5) is accepted with the reason above. L1–L6 are LOW, and none blocks merge.

Practice applied: Rule Zero, verify before you claim — `grep -c` reported 2 where the prior verdict said 3, and counting matches rather than lines showed both are right (3 hrefs on 2 lines), so the number now carries its unit instead of looking like a regression.
