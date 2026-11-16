> Round 2 claims check by a read-only claims-judge subagent, 2026-11-15 18:20–18:40 UTC. Reviewed text:
> - `README.md` and `docs/adr/0004-approved-ai-vendors.md` at `f3ebfef` (PR #50 head, pushed; `git ls-remote` exit 0).
> - `docs/assets/miami-ai-hackathon.jpg` at `f3ebfef`.
> - `/Users/jay/Projects/receipts-drafts/social-posts.md` and its attached PNG.
> - `video-src/index.html:134-142`, and `receipts-demo-narrated-v3.mp4` (sha256 `7b5930da…`).

# Claims verdict, round 2: W3 README (PR #50), social posts, video end card

**Texts checked:**
- **README and ADR-0004:** `git diff origin/main...HEAD -- README.md docs/adr/0004-approved-ai-vendors.md`. Head is `f3ebfef` and base is `d719360`, which is also `main` and the deployed SHA (`/healthz` at 18:25:55Z: HTTP 200, `"sha":"d719360"`, `x-receipts-mode: live`). The whole README was re-read. Line numbers are `README.md` at `f3ebfef`.
- **Social posts:** `social-posts.md`, all 87 lines, including the notes.
- **End card:** `index.html:134-142`, and the frame at 116 s of v3.

**Re-run artifacts.** These are in the scratchpad and are not durable: `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/w3claims-r2/`
- **The copy:** `copy-f3ebfef/` is `git archive f3ebfef`. `git diff --stat d719360 f3ebfef -- src tests pyproject.toml uv.lock` is empty (exit 0), so this code is the deployed code.
- **How the Python ran:** `env -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u DATABASE_URL -u DEMO_PASSCODE PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=…/copy-f3ebfef/src /Users/jay/Projects/receipts/.worktrees/w3-credits/.venv/bin/python <script>`, from an empty working directory.
  - Every script exited 0, with no network and no model or Keenable call.
  - The main checkout's `.venv` has no `rapidfuzz`, so round 1's `uv run --no-sync` only works from the worktree.
- **Scripts (`scripts/`):**
  - `meta_scan.py`;
  - `qr_detect.swift` (macOS Vision and CoreImage, with a positive control);
  - `people_detect.swift`;
  - `readme_examples.py` (round 1's script plus 5 cases);
  - `api_modes.py` (round 1's script);
  - `search_receipt_price.py`;
  - `window_limit.py`.
- **`web/`:** the GETs made at 18:25–18:35Z. These are `/healthz`, `/api/runs`, the 3 runs, the bodies of PR #46 and #29, issue #45, the landing page, the LiteLLM sites and the Mellea PyPI JSON. Round 1's saved official-site pages, still in `…/scratchpad/w3claims/web/`, were reused.
- **`img/`:** both photos, and the end-card frame `endcard-v3-116.png`.

## Verdict per text

1. **README and ADR-0004 (PR #50): PASS.** It has no HIGH finding. It has MEDIUM findings 4 and 5, and LOW findings 8, 9, 10, 11 and 12.
2. **Social posts: FAIL.** HIGH findings 1 and 2. It also has MEDIUM finding 3, and LOW findings 6, 7, 10 and 13.
3. **Video end card: PASS.** The v3 frame at 116 s matches `index.html:139-142` word for word. "organised by Agentic Day" is now on the card, which fixes round 1's finding 14.

## Round 1 findings: status at `f3ebfef`

| R1 # | Status | Evidence |
|---|---|---|
| 1 GPS EXIF | **Fixed** | Both current files carry no metadata (see "Attachments" below). The history blob was accepted by the owner and was not re-raised. |
| 2 Live settings | **Fixed** | `api_modes.py` (exit 0). With no environment: demo mode, POST 401. With the passcode only: POST 503 "KEENABLE_API_KEY is not set". With the passcode and Keenable key only, or with both keys and no `DATABASE_URL`: demo mode, POST 202 `run-demo-0001`, Acme vs Zeta. All 4 of 4 match README:23, :55, :195-197 and :369. The code is `wiring.py:4-6`, `:107-118`, `:221-223` and `:306-309`, and `routes.py:68-69`. |
| 3 "every price" | **Fixed in the README (:222). In the posts it is replaced by finding 1** | "$-price" closes the unsigned-price gap but not the search-receipt gap. |
| 4 "gated by … blind AI review" | **Reworded; now finding 3 (MEDIUM, no denominator)** | |
| 5, 6 Note scopes | **Fixed** | posts:85 and :57 name the places searched. Both claims hold where named (see below). |
| 7 Repairs on the deployed app | **Fixed** | README:21, posts:20 and X 2/ say the repairs were tested locally. `/api/runs` holds 3 runs. The newest started at 04:31:45Z, before #46 merged at 17:21:20Z, so no repair has run on the deployed app. |
| 8 "repairs what fails" | **Fixed** | posts:20 and X 2/. The budget is `repair.py:12-13` and `:178`. |
| 9, 10, 11 | **Fixed** | README:500-502 (see "Demo numbers" below). |
| 12 Not re-runnable | **Disclosed, not fixed: finding 4** | |
| 13 Limits list | **Fixed: 6 of 6** | The six are at `rules.py:47`, `:58`, `:77-79`, `:80-82`, `:86-87` and `:91-92` at `d719360`. All 6 of 6 reproduce: L1, B1, U1-U3, F1 and W1 in `readme_examples.py`, and WIN1 in `window_limit.py`. One bullet's wording is finding 8. |
| 14 End card | **Fixed** | The v3 frame. |
| 15, 16 | **Fixed** | README:311-312 and :232-233. The claim and quote appear in `run-0e7ff2b1bb05`; the run's claim has a trailing period. The page text is from `tests/test_verify_claim_numbers.py:62`. |
| 17 ADR-0004 Mel row | **Mel row fixed; two other rows still stale, and no dated note: finding 5** | |
| 18 QR decoder | **Fixed** | A decoder was run in this check (see "Attachments" below). |
| 19 Co-hosts | **The owner's call** | posts:87 lists them as optional. Luma's "Hosted By" list includes Miami Fintech Club and The AI Collective. |

## Claims that passed, and their evidence

### Attachments (README JPEG at `f3ebfef`, drafts PNG, v3 video)

- **"Its metadata is stripped: no GPS, device or capture time" (posts:3; commit `bca0d21`).** Checked three ways:
  - **`meta_scan.py` (exit 0), the JPEG (148,606 bytes):** only APP0 JFIF, DQT, DHT, SOF0 and SOS. It has no APP1 (no Exif or XMP), no APP2, no APP13 and no COM segment. There are 0 bytes after EOI. 0 of the 22 metadata byte strings occur (Exif, GPS, XMP, Apple, iPhone, `2026:11:14`, 8BIM, MPF and others).
  - **`meta_scan.py`, the PNG (1,187,770 bytes):** the chunks are IHDR, pHYs, cICP, cHRM, gAMA, 290 IDAT and IEND. There is no eXIf, tEXt, iTXt, zTXt or tIME. 1 of the 22 strings matches, "HDR", which is the IHDR chunk name.
  - **`sips -g all` (exit 0 on both) and `ffprobe -show_entries format_tags:stream_tags` (exit 0 on both):** no EXIF, GPS, device or time property.
  - **v3 video:** ffprobe tags show only the encoder (`Lavc62.28.101 libx264`) and the handler names. 0 location, make or model tags.
- **"the QR codes are blurred" (posts:3).** Checked by two methods, which agree:
  - **By eye:** both images show a smooth blurred band.
  - **`qr_detect` (exit 0):** the positive control, a QR made with `CIQRCodeGenerator`, was decoded by both Vision `VNDetectBarcodesRequest` and `CIDetector`. In 4 of 4 inputs (both full images, and 3× crops of the band) it found 0 symbols.
  - The note's "no QR decoder was run" is true of the writer, and is now out of date.
- **"cropped so that no attendee shows" (posts:3).** Checked by two methods:
  - By eye, on both images.
  - `people_detect` (exit 0) finds 0 faces and 0 people in 2 of 2 images. No positive control was run. Its text recognition reads only the screen and the podium.
- **README:536, the alt text.** It matches the image's text.

### README

- **:20 "the deployed app runs live comparisons".** Checked two ways, which agree:
  - `/healthz`: `x-receipts-mode: live` at `d719360`.
  - `/api/runs`: 3 of 3 runs are live, real company pairs.
  - The code path is `wiring.py:215-229`.
- **:21 "measured locally before deploy, not yet on the deployed app".**
  - PR #46's body, lines 33-43, gives the runs: 08:14:58–08:17:36Z, against a temporary SQLite file.
  - PR #46's body, line 83, says "Not measured on the deployed app".
  - The deployed run list has no run after 04:31:45Z.
- **:22, :23, :55 and :195-197, the passcode and the three settings.** Covered by R1 #2 above. "The UI replays it with no setup at all" is `wiring.py:308-309`.
- **:212-214 and :220-223, the rules.** `readme_examples.py` (exit 0) checks them:
  - E1, the edge cut, falls through to fuzzy: "numbers differ … page has $199 there".
  - E2 and E3 verify `quote_exact`.
  - C1: a claim saying `€5` against a quote saying `€20` gives "claim numbers not in quote: €5".
  - S2: a quote that repeats a price fails, as :221 says.
- **:232 "outputs … at commit `d719360`".** All 7 of 7 outputs (R1–R7) match README:239-323 character for character.
- **:225-230, the six limits.** All 6 of 6 reproduce: L1, B1, U1–U3, F1 and W1 verify, and WIN1 is rejected. The wording of :229 is finding 8.
- **:490-497, the demo table.** All 4 of 4 rows match `…/scratchpad/mellea/live_pairs.out:1-4` exactly, and match PR #46's body, lines 49-52. `git diff --stat 5af08c1 d719360 -- src tests` is empty (exit 0).
- **Demo numbers, :500-503.**
  - `run-3cc9b768f440`: 15 of 20 verified, and 5 of 5 failures are `claim numbers not in quote` (`live_reasons.out:1-6`).
  - `run-a7be7a53cba9`: 20 of 20 verified (`live_repaired.out:17`). In 6 of its 8 printed verified pricing claims, the quote lacks the plan name. Issue #45's comment 4, line 13, says the other 2 add a term.
  - Duplicates: issue #45's comment 4, line 17.
  - Settings: PR #46's body, lines 37-43.
- **:538-541, the event.** The Luma page (saved 17:37Z) says:
  - "Join Mel × ElevenLabs on Saturday, November 14, 2026, at Miami Dade College";
  - "Hosted by Agentic Day · Mel × ElevenLabs";
  - "Miami Dade College — Wolfson Campus".
- **:545, Mel's UI work.** PR #47's body, line 15: "Mel built `a31a101`, `c4f840d`, `bf26e30` and the repair `a94f668`". The drafting credit was already on `main`, and its only record is the owner's account.
- **:547-554, the stack.** Unchanged from round 1's evidence (`pyproject.toml`, `pricing.yaml:3`, `harness/live.py:61-68`, ADR-0005).
- **:555, "Claude Code built Wave 0 and lanes L1 to L5 … plus the live wiring".**
  - Issues #16 and #17 carry "(Claude Code)" in their titles.
  - PRs #22 and #24–#28 end "Generated with Claude Code".
  - In PR #27 (L4), 7 of its 9 commits carry "Co-Authored-By: Claude Fable 5.1"; the other 2 are merges.
  - In PR #29, 7 of its 10 commits carry a Claude co-author line.
  - The plan file `docs/superpowers/plans/2026-11-14-w0-foundations-and-w1-lanes.md:26` says "Claude Code builds W0 and L1–L5 … No Codex lane".
- **Links:** 21 of the 21 non-LinkedIn URLs in the README diff and the posts return HTTP 200 (GET, 18:3xZ). LinkedIn returns 403 or 999 to scripted requests for 13 of its 14 URLs.

### ADR-0004 (the Mel row only)

- **"Lane L5 itself was built by Claude Code (issue #17)" and "builds UI follow-ups … #40 (PR #47)".** Issue #17's title, PR #26's footer, and PR #47's body, line 15.

### Social posts

- **posts:18 and LinkedIn's description of the product.** The receipt types are in `contracts.py:33-47`. "plain-code verifier, no language model" is `rules.py:1-4`.
- **posts:20 "first live run showed 24 of 24 … some quotes didn't carry the claim's prices".**
  - `GET /api/runs/run-0e7ff2b1bb05` returns 24 claims, 24 of them verified.
  - Its Warp Build, Warp Max and Business claims carry prices their quotes lack.
  - The word "first" is finding 6.
- **posts:20 "every number in a loosely matched quote must sit where the page has it".** `rules.py:39-46`. Re-runs R7 and S2 both fail.
- **posts:20 "up to two rewrites … the verifier still has the final word … tested in local live runs so far".** `repair.py:12-13`, PR #46's body line 4, and the deployed run list.
- **posts:22, posts:72 and posts:83, the event credits.** The Luma page, as for README:538-541.
- **posts:31 "CI tests on every change".**
  - Ruleset 27284472 is active. It was created at 22:33:31Z on 2026-11-14, has no bypass actors, and requires `ci-python` among 5 checks.
  - `ci-python.yml` has no path filter and runs pytest.
  - All 23 of 23 merged PRs show `ci-python` SUCCESS (`gh pr view N --json statusCheckRollup`, exit 0).
  - The only first-parent commit on `main` that did not come through a PR is the bootstrap, `419dad6` (22:33:01Z), which predates the ruleset.
- **posts:40-53, the LinkedIn table.** All 14 of the 14 URLs appear on the organisation's own site.
- **X handles, posts:72 and :77.**
  - 14 of the 15 handles appear as links on the organisation's own site.
  - `@IBMResearch` is the `twitter:creator` meta tag on research.ibm.com, which posts:83 covers as "page data".
  - So all 15 of 15 are confirmed.
- **posts:56 "gradio.app links no LinkedIn page".** The gradio.app home page has 0 LinkedIn links.
- **posts:57 "mellea.ai and its PyPI page link no LinkedIn or X account".**
  - mellea.ai has 0 links to either.
  - PyPI's JSON API for `mellea` 0.9.0 has `project_urls: null`, and its description holds 0 LinkedIn or X links.
  - The PyPI HTML page served a 3 KB bot challenge.
- **posts:85 "No event hashtag appears on the Luma page, agenticdaysummit.com or openmel.dev".** A hashtag regex over the visible text of all 3 pages finds only CSS colour codes and anchor names.
- **posts:87, the co-hosts.** Luma's "Hosted By" list includes Miami Fintech Club and The AI Collective.
- **X thread length.** With X's weighting, the three posts come to 243, 277 and 220 of the 280 allowed.

### End card (`index.html:134-142`, and the v3 frame at 116 s)

- **Text:** it matches the HTML word for word.
- **Tracks:** Luma lists "2. 📣 Agentic Marketing" and "8. 🧠 Research, Productivity & Developer Agents".
- **Credits and stack:** the same evidence as README:538-555.
- **"Built with Claude Code and Mel":** README:545 and :555.

## Findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| 1 | posts:20 "Every $-price in a claim must be in its quote." and X 2/ "Now every $ price must be in its quote" | I1 (contradicted by a re-run) | HIGH | **Search receipts:**<br>• `search_receipt_price.py` (exit 0): the claim "Warp Build is $18/month on the annual plan." with a `SearchReceipt` whose logged row's snippet says $20 verifies (`search_log`).<br>• `rules.py:93-96` at `d719360` takes search receipts out of the claim-number rule.<br>• `pricing.yaml:8-10` lets pricing claims "cite a search you ran with its query, rank and result URL".<br>**"$ 25":** X's "$ price" also covers `$ 25`, which verifies against a quote saying `$20` (re-run U3). README:227 calls it unsigned.<br>**Observed rate:** in the 3 deployed runs, 0 of 21 pricing claims used a search receipt, and 0 of 18 search-receipt claims carried a signed price.<br>Round 1's suggested wording missed this. | LinkedIn: "Every $-price in a claim backed by a quote must be in that quote." X: "every $-price in a quoted claim must be in its quote". |
| 2 | posts:58 "LiteLLM: its two official links point to different page addresses that couldn't be confirmed as the same page." | I1 / I2 (no source; a negative with no scope) | HIGH | The note names neither link, nor how sameness was checked. My check: litellm.ai links `linkedin.com/company/90867735`, and docs.litellm.ai links `linkedin.com/company/berri-ai/` (both fetched 200, saved in `web/`). LinkedIn returns 403 or 999 to scripted requests, so neither could be resolved. The claim holds where I looked. | Name both: "litellm.ai links /company/90867735 and docs.litellm.ai links /company/berri-ai; LinkedIn blocks scripted checks, so they could not be matched." |
| 3 | posts:31 "a blind AI review before nearly every merge" | Numbers (no set or denominator) | MEDIUM | Set: the 19 merged non-Dependabot PRs.<br>• 15 of 19 had a PASS verdict file before merge: #21-29, #32, #36, #38, #43, #46 and #47. Verdict-file mtimes (UTC) precede `mergedAt`. The folder is untracked.<br>• 2 more had only FAIL reviews before merge: #11 (rounds 1-2 FAIL, round 3 "pending", per its body lines 14-16) and #35 (6 FAIL verdicts, merged on the owner's decision, body lines 2 and 60).<br>• 2 of 19 had none: #30 was "merged before the verdict" (PR #31's body, line 1), and #31 has no verdict.<br>So 17 of 19 had a review and 15 of 19 had a pass. The 4 Dependabot merges (#2-#5) had no review. | Say "before 17 of its 19 merges (15 with a passing verdict)", or put that count in the notes. |
| 4 | README:490-497, the four live runs, and :504 "Not reproducible from this repository" | I6 (cannot be re-run) | MEDIUM | The README now discloses the gap, but the measurement still cannot be re-run from a durable artifact. The runner scripts still exist only at `…/scratchpad/mellea/live_pairs.py`, `live_reasons.py` and `live_repaired.py`, all present at 18:3xZ, and a reboot can clear them. This is round 1's finding 12, partly addressed. | Commit the three scripts (for example under `scripts/`, with no keys), or quote their command, environment and expected output in the README. |
| 5 | ADR-0004 at `f3ebfef`: the new Mel row "Lane L5 itself was built by Claude Code (issue #17)", beside the unchanged line 23, "Claude Code builds W0, L1–L3, L6, W2 and W3", and the Codex row, "Builds lane L4 (`db/`, `api/`)" | I5 (the correction has no dated note), and record consistency | MEDIUM | One table now contradicts itself, and contradicts README:555 ("lanes L1 to L5"). Issue #16's title says "(Claude Code)". In PR #27, 7 of its 9 commits carry "Co-Authored-By: Claude Fable 5.1". The plan file says "No Codex lane" (`plans/2026-11-14-w0-foundations-and-w1-lanes.md:26`). The Mel-row fix has no dated note. AGENTS.md:12 asks to fix the top of the record, and ADR-0007:5 shows the repo's dated-note pattern. | Correct line 23 to "W0, L1–L6, W2 and W3", and correct or drop the Codex row. Add a dated correction line under ADR-0004's title. |
| 6 | posts:20 "Our first live run showed 24 of 24" and X 2/ "First live run: 24/24" | I1 (precision) | LOW | Two earlier live runs are on record. `run-f817acdb7ff6` was 22/22 at 01:34 UTC (`verdicts/2026-11-15-w2-orchestrator-judge.md:19`, `2026-11-15-w2.md:52`). `run-6a5fe9499c4d` was 25/25 at 01:43:56Z (`w2-orchestrator-judge.md:16`). `run-0e7ff2b1bb05` started at 01:43:54Z. It is the earliest of the 3 runs on the deployed app. "First" comes from issue #33's body. | "Our first run on the deployed app" or "an early live run". |
| 7 | X 1/ "every claim must carry a receipt: a quote from a page they fetched" | I1 (incomplete) | LOW | 18 of the 64 claims in the 3 deployed runs carry a search receipt, all of them positioning_seo (`web/run-*.json`). | Add "or a search result they logged". |
| 8 | README:229 "Values swapped within one quote still verify." | Clarity (reads as contradicting :221 and :316-324) | LOW | Read alone, it contradicts :221 ("A quote that swaps … the page's prices fails") and the example at :316-324. Re-runs R7 and S1 are `verified=False`. The limit is on the claim side: W1, the claim "Pro is $19 yearly and $199 monthly." on the quote "Pro yearly: $199. Pro monthly: $19.", verifies (`rules.py:91-92`). | "A claim that swaps two values its quote carries still verifies." |
| 9 | README:214 "a value in the claim (a price, a `%`, a decimal or a thousands number) is not in the quote → not verified", and :222 "every value in the claim must also be in its quote" | Scope | LOW | **:214:** "a price" is unqualified, but unsigned prices verify (U1-U3), as :227 admits.<br>**Search receipts:** the README never says that claims with a search receipt skip this rule (`rules.py:95-96`; re-run SR1). | At :214 say "a price written with a currency sign". Add a limit bullet: "Claims with a search receipt are not checked against any text." |
| 10 | README:543 and posts:6 and :28, the "Ask Receipts" voice agent | Clarity | LOW | The landing page's button and footer say "Talk to Receipts": 3 of 3 mentions, and 0 "Ask Receipts" (`web/landing.html`, 200). ADR-0004:34 names the agent "Ask Receipts". | Say "the 'Talk to Receipts' voice button", or just "the voice agent". |
| 11 | README:542-544, Mellea listed under "Sponsors in the product" | I1 (an internal source only) | LOW | The sponsor status rests on the owner's statement: issue #39's body, line 1, and ADR-0007:9. The Luma page has 0 mentions of IBM or Mellea and no sponsor list; agenticdaysummit.com has 0 mentions of Mellea. The README cites ADR-0007 for the repair loop, not for the sponsorship. | Cite issue #39 for the sponsor status, or have the owner confirm it. |
| 12 | README:480-483 (already on `main`) "The ruleset does not enforce this; every builder follows it as a rule" | Completeness | LOW | The README does not say that the owner merged #30 before its verdict (PR #31's body, line 1) or #35 after 6 FAIL verdicts (PR #35's body, lines 2 and 60). | Add "the owner waived it for #30 and #35". |
| 13 | posts:29 "@Mel for the demo script, the architecture diagram and UI work" | Precision | LOW | README:545 says "the **first** architecture diagram (corrected against the code for this README)". | "a first architecture diagram". |

## Outside the rubric (not a finding)

The Luma page (saved 17:37Z) includes a judging rule: "🤖 Mandatory: Build Your Entire Project with Mel … Projects not built with Mel are not eligible for judging or prizes." The README (:555) and the posts (posts:31, "Claude Code, which built most of it") accurately say that Claude Code built most of the project. The texts are not wrong. The owner may want to see this before posting publicly.

VERDICT: FAIL
