> **Redacted 2026-11-15 at the owner's request:** finding 2's evidence from the owner's private local Codex records (session id, times, folder and file names, settings) is withheld; the finding and its fix are unchanged.

> Round 3 claims check by a read-only claims-judge subagent, 2026-11-15 18:44–19:00 UTC. Reviewed text:
> - `README.md`, `docs/adr/0004-approved-ai-vendors.md` and `scripts/mellea/*.py` at `ea455ef`. This is the PR #50 head; `git ls-remote` gave `ea455ef` at 18:59:48Z. The base is `d719360`.
> - `/Users/jay/Projects/receipts-drafts/social-posts.md` (87 lines), as it stood at 18:4xZ.
> - The PR #50 description draft `…/scratchpad/w3/pr50-body.md`, re-read after it changed on disk at about 18:53Z (29 lines, now with "Scope" and "Tests" paragraphs). `{CI}`, `{CLAIMS}` and `{JUDGE}` were not checked.
> - The end card was skipped: it is unchanged and passed round 2.
>
> **Privacy note:** finding 2 relied on the owner's local Codex records; those details are withheld (see the note above).

# Claims verdict, round 3: W3 README (PR #50), ADR-0004, Mellea scripts, social posts, PR description

**Base and deploy.**
- `/healthz` at 18:45:16Z returned HTTP 200, `"sha":"d719360"` and `x-receipts-mode: live`.
- `git diff --stat d719360 ea455ef -- src tests pyproject.toml uv.lock` is empty (exit 0), so the code under the README is the deployed code.

**Worktree state during the check.**
- The worktree has uncommitted edits, first seen at about 18:52Z:
  - `README.md:508` now gives `live_reasons.py 1` and `live_repaired.py 1`;
  - `scripts/mellea/live_reasons.py:5-7` drops the `claim repair:` clause.
- They are not in `ea455ef` and are not pushed. They fix two parts of finding 7. Re-check that diff once it is committed.

**Re-run artifacts.** These are in the scratchpad and are not durable: `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/w3claims-r3/`
- **The copy:** `copy-ea455ef/` is `git archive ea455ef`.
- **How the Python ran:** `env -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u DATABASE_URL -u DEMO_PASSCODE PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=…/copy-ea455ef/src …/w3-credits/.venv/bin/python`, from `emptycwd/`. No script under `scripts/mellea/` was executed, and no model or Keenable call was made.
- **Scripts (`scripts/`), all exit 0:**
  - `ast_compare.py`;
  - `script_api_check.py`;
  - `dollar_price_edges.py`;
  - `suffix_rate.py`;
  - `x_weight.py`.
- **`web/`:** litellm.ai, docs.litellm.ai and the landing page, fetched at 18:54Z.
- **Logo files:** `app-logo-on-black.png` and `landing-logo-head-on-black.png`.
- **Reused from round 2** (`…/w3claims-r2/`): `web/run-*.json` and `img/drafts.png`.

## Verdict per text

1. **README, ADR-0004 and `scripts/mellea/` (PR #50 at `ea455ef`): FAIL.**
   - HIGH finding 2 is in ADR-0004:34.
   - The README on its own has no HIGH. It has MEDIUM findings 3 and 4, and LOW findings 5, 6 and 7.
   - The scripts have LOW finding 7.
2. **Social posts: FAIL.** HIGH finding 1. It also has MEDIUM finding 4, which is the owner's call.
3. **PR #50 description draft: PASS.**
   - It has no HIGH: LOW finding 8, and LOW finding 5 applies to its line 5.
   - Lines 9 and 14 (`bin/jig` "at `ea455ef`") must be refreshed if fixes land in a new commit.

## Round 2 findings: status at `ea455ef` and in the posts

| R2 # | Status | Evidence |
|---|---|---|
| 1 HIGH "$-price" | **Fixed as worded in round 2, but a new gap makes the sentence false again: finding 1 (HIGH)** | LinkedIn :20 "backed by a quote" and X 2/ "a quoted claim's" now leave out search receipts. Re-run SR1 (search receipt, `$18` against a `$20` snippet) still verifies, which the new wording permits. |
| 2 HIGH LiteLLM note | **Fixed** | posts:58 names both links. At 18:54Z, litellm.ai (HTTP 200) links `linkedin.com/company/90867735` (2 occurrences), and docs.litellm.ai (HTTP 200) links `linkedin.com/company/berri-ai/` (1). LinkedIn returned 403 to scripted GETs of both. |
| 3 MEDIUM review count | **Fixed** | posts:31 says "17 of the first 19, not counting dependency updates". `gh pr list --state merged` (exit 0) still shows 19 non-Dependabot merges: #11, #21–#32, #35, #36, #38, #43, #46 and #47, plus Dependabot's #2–#5. In 15 of those 15 PRs, a `VERDICT: PASS` file's UTC mtime precedes `mergedAt`; the margins run from 27 s (#36) to 8 h 44 min (#46). #11 had two FAIL rounds before merge (its body:15-16), and #35 had 6 FAILs. So 17 of 19 had a review before merge. #30 and #31 had none. |
| 4 MEDIUM not re-runnable | **Fixed. LOW residue: finding 7** | The three scripts are committed. `ast_compare.py` (exit 0): in 3 of 3, the AST is equal to the scratch original once the module docstring is set aside. `diff` shows the remaining code differences are line wrapping only. Each original's mtime precedes its run: 08:14:33Z before 08:14:58Z, 08:17:00Z before 08:17:01Z, and 08:17:35Z before 08:17:36Z. `script_api_check.py` (exit 0): every name the scripts use exists at `d719360` (`build_live_service(…, repo, repair_factory)`, `start`/`events`/`wait`, the event fields, and `SqlRunRepo`/`create_schema`). `specialist.py:370` logs `claim repair: <domain> failing=N repaired=M`. `settings.py:17` has no `env_file`, so "keys come from the environment" holds. |
| 5 MEDIUM ADR-0004 | **Fixed. New HIGH in the edited Codex row: finding 2** | There is a dated correction at ADR-0004:5-7, and rows :27, :33 and :34 were edited. Its sources hold: issue #16's title ends "(Claude Code)", PR #27 is gh-16 (L4), PR #26 is gh-17 (L5), and plan :26 says "No Codex lane". |
| 6 "first" | **Fixed** | posts:20 "An early live run" and X 2/ "Early live run". |
| 7 X 1/ | **Fixed** | posts:67 adds "or a search result they logged". |
| 8 swap wording | **Fixed** | README:229. Re-run W1 (the claim swaps two values its quote carries) gives `verified=True`. |
| 9 scope | **Fixed as suggested. LOW residue: findings 5 and 6** | README:214 now says "a price written with a currency sign". :231-232 is the new limit, which matches `rules.py:93-96`, and re-run SR1 agrees. |
| 10 button | **Fixed** | README:550 and posts:6. The landing page (HTTP 200, 18:54Z) has 3 "Talk to Receipts" and 0 "Ask Receipts". |
| 11 Mellea sponsor | **Fixed** | README:551-552 cites issue #39. `gh issue view 39` body:1 says "a hackathon sponsor". |
| 12 waivers | **Fixed as suggested. New MEDIUM in the count: finding 3** | README:485-486. PR #31 body:1 says "merged before the verdict at the owner's request", and PR #35 body:2 and :111 record the waiver. |
| 13 diagram | **Fixed** | posts:29 "a first architecture diagram". |
| Attachment note (QR decoder) | **Fixed** | posts:3 relies on round 2's `qr_detect`: macOS Vision and CoreImage, with a positive control, found 0 symbols in 4 of 4 inputs. The files are unchanged since round 2. The drafts PNG's sha256 `06ca5ef53292…` equals round 2's `img/drafts.png`. The v3 video is `7b5930da8c8f…`. The README JPEG blob is `12d2bc29` at `bca0d21`, `f3ebfef` and `ea455ef` alike. |
| X lengths | **Confirmed: 275, 278 and 220 of 280** | `x_weight.py` (exit 0) uses twitter-text v3 weights: URLs count 23, emoji count 2, and `×` (U+00D7) counts 1. |

## Claims that passed, and their evidence

### README (`ea455ef`)
- **:507-511 "Re-running them …":**
  - The script names are right, as is `live_pairs.py 2`: `live_pairs.out` holds 2 pairs.
  - "They need `ANTHROPIC_API_KEY` and `KEENABLE_API_KEY`": each script's `main` checks both and prints SKIP otherwise.
  - "a temporary SQLite file, not Neon": `SqlRunRepo(url="sqlite:///…tmp…")` in all 3 of 3 scripts.
  - "unchanged apart from their docstrings and line wrapping": `ast_compare.py` plus `diff`, above.
- **:229 and :231-232:** re-runs W1 and SR1 in `dollar_price_edges.py`.
- **:485-486:** both named waivers are sourced, as in R2 #12 above.
- **:550-552:** R2 #10 and #11 above.

### ADR-0004 (`ea455ef`)
- **:5-7 and :27, "Claude Code built W0 and lanes L1 to L6":**
  - Plan scope-cut row 1 (plan :26) gives W0 and L1–L5.
  - L6: the plan's l6-landing dispatch (plan :45).
  - 5 of the landing repository's 7 commits carry a Claude `Co-Authored-By` trailer. The other 2 are `c65d707` (the template import) and `0f7d0ce`, which the L6 judge reviewed.
- **:34 "Approved, but built no lane":**
  - 0 of the 140 commits on local refs have a Codex trailer (`git log --all`). Their trailers are Claude Opus 5.5 (50), Claude Fable 5.1 (49) and dependabot (4).
  - 1 commit message mentions Codex, and that is `ea455ef` itself.

### Scripts (`ea455ef`)
- `live_pairs.py:7`: "table came from `live_pairs.py 2`".
- `live_reasons.py:8`: "`run-3cc9b768f440`".
- `live_repaired.py:8`: "`run-a7be7a53cba9`".
- All three match `…/scratchpad/mellea/live_{pairs,reasons,repaired}.out`.

### Social posts
- **posts:20 and X 2/, the "Early live run" and "up to two rewrites … tested in local live runs" sentences:** unchanged evidence from round 2.
- **The thread's handles:** the 15 unique handles in X 2/ and X 3/ match round 2's 15 of 15 confirmed.
- **posts:31:** R2 #3 above.

### PR #50 description draft
- **:1:** `/healthz` at 18:45:16Z.
- **:5, "seven re-run examples":** two sources agree. Round 2 (r2 :90) found 7 of 7, and the blind judge (`verdicts/2026-11-15-w3-credits-judge.md:29`) found 7 of 7. ":5 … plus the search-receipt exemption" correctly keeps that limit apart from #45.
- **:7:** `ast_compare.py`.
- **:8:** the attachment hashes above.
- **:9:** the ADR-0004 evidence above.
- **:11, the photo history:**
  - The `18caf71` blob still has an Exif marker and a GPS IFD tag (presence only; no values printed).
  - `git merge-base --is-ancestor 18caf71 origin/jay/w3-readme-credits` exits 0.
  - Round 1's `gps_distance.py` put the point about 70 m from the venue's Luma coordinates.
  - The owner's acceptance is in `~/.claude/projects/-Users-jay-Projects-receipts/memory/handoff-2026-11-15.md:83` ("Jay ACCEPTED it at ~18:20 UTC"). See finding 8.
- **:14:** the judge's verdict, line 19, gives `bin/jig` exit 0 at `ea455ef`.
- **:18:** round 1 has 19 findings and ends `VERDICT: FAIL` (round 1 :108). Round 2 says README PASS and posts FAIL.
- **:21:**
  - `briefs/W3-ship.md:26` lists `scripts/` and "ADRs" under `Forbidden:`.
  - The finding numbers are right: R1 #17, R2 #4 and R2 #5.
- **:23:**
  - `pyproject.toml:61` has `include = ["src", "tests"]`.
  - `pyright scripts/mellea` (run in the copy) exits 1 with 3 errors, at `live_pairs.py:55`, `live_reasons.py:56` and `live_repaired.py:56`. All three come from the `**kwargs` dict being inferred as `dict[str, None]`.
  - "only `repair_factory` is passed" is right: `kwargs = {} if repairs_on else {"repair_factory": None}`.
- **:27:**
  - Issue #39 body:16 says "README and the demo video credits name Mellea".
  - Issue #45's title is "Verifier: bare-integer counts and 'free' negation".

## Findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| 1 | posts:20 (LinkedIn) "Every $-price in a claim backed by a quote must be in that quote." and posts:74 (X 2/) "Now a quoted claim's $-prices must be in its quote." | I1 (contradicted by a re-run) | HIGH | **What `dollar_price_edges.py` (exit 0) shows:**<br>• Controls: a claim's `$25` against a quote's `$20` is not verified ("claim numbers not in quote: $25"), and `$20` against `$20` verifies.<br>• A claim's "$20k", "$20K" or "$20M" per year against the quote "Enterprise starts at $20 per seat per month" all give `verified=True, quote_exact`. `_claim_values("…$20k…")` returns `['$20']`, so the suffix is dropped.<br>• "$.99" and "25$" verify too: neither is extracted.<br>• "$0" against a quote saying "not free" verifies. README:228 discloses that one; the posts do not.<br>**Where it is (not) disclosed:** README:226-232, issue #45 (0 of its 5 texts mention suffixes) and `rules.py:31-32` all fail to disclose the suffix case. `rules.py:31-32` says only that "`1.5k` is not `1,500`".<br>**Observed rate:** 0 of the 64 claims in the 3 deployed runs use these spellings (`suffix_rate.py`, exit 0). The absolute "Every" is still false. Round 2's suggested wording missed this. | Do not state the check as a guarantee. LinkedIn: "The verifier checks each $-price in a quoted claim against that quote (known gaps, such as `$20k` read as `$20`, are listed in the README)." X 2/: "Now a quoted claim's $-prices are checked against its quote." That adds 9 characters to a post at 278 of 280, so trim elsewhere (" Thanks 🙏" counts 10). Then add the README bullet from finding 5. |
| 2 | ADR-0004:34, OpenAI Codex CLI row, "What it receives": "Nothing so far; repository code if it is used". It is also the basis of ADR-0004:5-7's "now match the record". | I2 (negative claim with no scope), contradicted | HIGH | **What Codex received:** the owner's local Codex session logs (details withheld at the owner's request) show the owner used Codex Desktop (OpenAI) on 2026-11-15 to generate the Receipts logo.<br>**What shipped:** landing commit `2eebbf7` ("feat: owner's Receipts logo in navbar and footer") adds `public/logo.png`; `src/receipts/ui/assets/logo.png` came in with `002b2ae` (#36), which is in the deployed `d719360`. Seen on black, both shipped logos are crops of the Codex output.<br>**Repository code:** the logs name no repository path (details withheld).<br>**Why HIGH, not CRITICAL:** OpenAI is approved (ADR-0004:48), and nothing shows code or run data was sent. | Scope the negative and record the logo. For example: "No repository code so far (0 of 140 commits carry a Codex trailer; Codex's local session logs name no repository path). The owner used Codex Desktop (OpenAI) on 2026-11-15 to generate the Receipts logo, now in the landing page and the app; it received that request." How much of this to publish is the owner's call; the bare "Nothing" has to go. |
| 3 | README:485-486 "The owner waived it twice: PR #30 merged before its verdict, at the owner's request, and PR #35 merged on the owner's decision without a passing review." | Numbers (a count with no set or denominator; reads as exhaustive) | MEDIUM | Set: the 19 merged non-Dependabot PRs. 15 of 19 had a PASS verdict before merge (table above). 4 of 19 merged without one:<br>• #30, waived (PR #31 body:1);<br>• #35, waived (PR #35 body:2 and :111);<br>• #11, merged with "`/judge` round 3: pending" (PR #11 body:17) after two FAILs;<br>• #31, with no verdict: 0 verdict files are about it (it is mentioned only in the round 1 and 2 claims files), 0 GitHub reviews or comments, and its body:7 cites only `bin/jig` and the leak gate.<br>Read after "every builder follows it as a rule", "twice" implies the other 17 followed it. The posts' own "17 of the first 19" counts a different set. | "Of the 19 merged non-Dependabot PRs, 15 had a passing verdict before merge. The owner waived the rule for #30 (merged before its verdict, at the owner's request) and #35 (merged without a passing review); #11 merged with its third review pending, and #31, the fix-forward for #30, had none." |
| 4 | README:563 "**Claude Code** built … the landing page …", and the credits lists at README:541-563, posts:24-31 and X 3/, which name no maker for the logo | Attribution (incomplete) | MEDIUM | The logo in the landing page and the deployed app was generated with Codex Desktop (finding 2's evidence). No credit names that.<br>The W3 brief requires naming what each tool "actually did" (`briefs/W3-ship.md:17`, "Codex and Mel are named only for what they actually did (Codex: nothing in the final build …)"). That premise is now contradicted, and so is PR #30's body:12, "Codex is not credited".<br>No sentence in the texts states something false. This is an omission. | The owner decides. For example, add to the credits: "The logo was generated by the owner with OpenAI's Codex app." The posts can stay as they are. |
| 5 | README:214 and :222, "a price written with a currency sign … is not in the quote → not verified" and "every value in the claim must also be in its quote: a price written with a currency sign (`$20`, `€5`)"; also PR body:5 "the claim-number rule for prices written with a currency sign" | Scope | LOW | Same re-runs as finding 1. `$20k`, `$20M`, `$.99` and `25$` are written with a currency sign and are not checked as written. :227 calls `$ 25` "unsigned", though it carries a sign. The README frames the rule with a limits list, as round 2's finding 9 did, but the list misses this case. | Add a limit bullet: "A suffixed or trailing-sign price in the claim (`$20k`, `$1.2M`, `25$`, `$.99`) is read as `$20`, `$1.2` or not at all, so it can verify against a quote that lacks it." |
| 6 | README:225 "The rules have known limits, tracked in issue #45 and described in `rules.py`'s docstring:", which now heads the new :231-232 bullet | I1 (one of 7 bullets has the wrong source) | LOW | `gh issue view 45` (exit 0): the body and 4 comments cover labels, bare counts, unsigned prices, "free", swaps and the window, which are 6 of the 7 bullets. 0 of the 5 texts mention search receipts. The bullet's source is `rules.py:93-96` only. PR body:5 gets this right. | "… tracked in issue #45 (the search-receipt one is in `rules.py` only) …", or add it to #45. |
| 7 | README:507-511 "`live_reasons.py` and `live_repaired.py` for the two separate runs … a new run gives new run ids and … new counts", and `live_reasons.py:5-7` (at `ea455ef`) "Prints … the per-domain `claim repair:` log lines (repairs-on runs only)" | I6 (re-run parameters) and clarity | LOW | Both scripts default to 2 runs (`live_reasons.py:97`, `live_repaired.py:103`), but `live_reasons.out` and `live_repaired.out` each hold 1 run ("run 1" only). `live_reasons.py:94` runs only with repairs off, so it never prints a repair line. "gives … new counts" is definite, but counts can repeat. The blind judge raised the first two as LOW 4 and 6. Both are fixed in the uncommitted working tree, not in `ea455ef`. | Commit the working-tree fix. Change "new counts" to "can give different counts". |
| 8 | PR body:11 "The owner accepted that on 2026-11-15" and PR body:21 "added by the main session under the owner's delegation to merge" | I1 (no record named) | LOW | Both records exist only in private memory:<br>• the acceptance is in `handoff-2026-11-15.md:83`, "~18:20 UTC";<br>• the delegation is in `hackathon-build-state.md:11`, which quotes the owner.<br>The body names neither. The quoted delegation covers merging "on blind-judge PASS + green CI". It says nothing about widening the brief's scope, and the body's next sentence admits the widening. | Cite the session and time, as PR #35's body does (session `477932e0`, ~18:20 UTC). Say the scope widening was the main session's call, or get the owner's OK. |

## Outside the rubric (not a finding)

- Round 2's note still applies. The Luma page's rule says "Mandatory: Build Your Entire Project with Mel … Projects not built with Mel are not eligible for judging or prizes". The texts accurately say that Claude Code built most of the project. Finding 4 adds a third tool, Codex, behind the logo.
- The PR body draft changed on disk during this check, and the version reviewed is the 29-line one with "Scope" and "Tests".

VERDICT: FAIL
