> Saved by the main session at ~18:25 UTC 2026-11-15 from claims-judge agent aaa667ccce2eea811's report (round 1; the agent was read-only). Reviewed text: README at 18caf71.

# Claims verdict: W3 README (PR #50), social posts, video end card

**Texts checked:**
- **README:** `git diff origin/main...HEAD -- README.md` in `/Users/jay/Projects/receipts/.worktrees/w3-credits`. Head is `18caf71`, base is `d719360`. Line numbers below are `README.md` at `18caf71`.
- **Social posts:** `/Users/jay/Projects/receipts-drafts/social-posts.md`.
- **End card:** `/Users/jay/Projects/receipts-drafts/video-src/index.html:134-142`, and the frame at 116 s of `receipts-demo-narrated-v2.mp4`.

**Re-run artifacts (scratchpad, not durable):** all under `/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/w3claims/`.
- **The copy of `d719360`:** made with `git archive d719360` into `copy-d719360/`, with no `__pycache__`.
- **Scripts:** all in `scripts/`. Each ran with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=copy-d719360/src uv run --no-sync`. Each exited 0.
  - `readme_examples.py`: the README's verifier examples and related cases.
  - `api_modes.py`: the app in-process under four environments.
  - `exif_tags.py` and `gps_distance.py`: the photos' metadata.
- **Fetched pages:** in `web/` (the Luma page and the official sites).
- **Images:** `endcard-116.png` (the end-card frame) and `qr-band-zoom.png` (the blurred QR band, zoomed).

## Verdict per text

**1. README (PR #50): FAIL.** HIGH findings 1, 2 and 3.

**2. Social posts: FAIL.** HIGH findings 1 (the attached PNG), 3, 4, 5 and 6.

**3. Video end card: PASS.** The rendered frame at 116 s matches `index.html:134-142` word for word, and every name and link on it checks out. It leaves out the organiser, Agentic Day. That makes the post's line 3 ("credits everyone") false, which is finding 14 and is counted against the posts.

## Claims that passed, and their evidence

### README

- **Line 20, "the deployed app runs live comparisons".**
  - `curl /healthz` returned HTTP 200 with `"sha":"d719360"` and the header `x-receipts-mode: live` (17:34:04Z).
  - `GET /api/runs` lists 3 live runs (AMD vs Nvidia, and Mel vs Warp twice).
  - The live path is `wiring.py:215-238` at `d719360`.
- **Line 22, the passcode.** `routes.py:24` and `:68` at `d719360`. The GET routes at `:73` and `:80` take no passcode, and my unauthenticated GETs returned 200.
- **Line 55, two packs in parallel; the demo covers pricing only.** `wiring.py:95` and `:153`, and `ui/demo.py:76` (`domains=("pricing",)`).
- **Lines 212-214 and 220-223, the verifier rules.**
  - The rules are in `rules.py`'s docstring at `d719360`, lines 33-46 and 72-92.
  - The edge-cut case (`Basic is $19` on a `$199` page) falls through to the fuzzy check: "numbers differ (quote has $19; page has $199 there…)".
  - `$20.00` equals `$20`, and `20 percent` equals `20%`: both verify `quote_exact`.
- **Line 227, "outputs … at commit `d719360`".** All 7 of the 7 example outputs reproduced character for character (`readme_examples.py`, exit 0).
- **Line 364, "202 with {"run_id": "run-…"}".** `routes.py:60` and `service.py:37`.
- **Line 485, "Live, on 2026-11-15, with the code now on `main`".**
  - `git diff --stat 5af08c1 d719360 -- src tests` is empty (exit 0).
  - The temporary SQLite file is `live_pairs.py:50`.
  - The output files are timestamped 2026-11-15T03:16-03:17-05:00.
- **Lines 487-492, the run table.** All 4 rows match `mellea/live_pairs.out:1-4` exactly: run ids, counts, dropped and wall times.
- **Line 529, the photo's alt text.** Matches the photo.
- **Lines 531-534, the event.**
  - The Luma page says: 2026-11-14, 12:00-20:00 ET; "Join Mel × ElevenLabs"; "Hosted by Agentic Day · Mel × ElevenLabs"; "Miami Dade College — Wolfson Campus, 300 NE 2nd Ave".
  - The screen in the photo reads "mel × ElevenLabs Presents".
  - agenticdaysummit.com says the hackathon was "organized by Agentic Day with Mel and ElevenLabs".
- **Line 536, ElevenLabs.** `docs/adr/0004-approved-ai-vendors.md:34` (ADR-0004). The landing page's HTML shows "Talk to Receipts" and ElevenLabs (3 hits each).
- **Line 537, Mellea.** The `mellea-0.9.0` package metadata gives an Apache license classifier, the contact `melleaadmin@ibm.com`, "started by IBM Research" and https://mellea.ai. Also ADR-0007, line 9.
- **Line 538, Mel's UI work and OpenAI key.** PR #47's body, line 15, and ADR-0004:29.
- **Lines 540-547, the stack.** Model `claude-sonnet-5-5` in `pricing.yaml:3` and `positioning_seo.yaml:3`. The dependencies in `pyproject.toml`. LiteLLM is Mellea's client in `harness/live.py:61-68`. Neon is in ADR-0005:13. Pydantic is in `contracts.py:24-27` and `settings.py:16`.
- **Line 548, Claude Code's role.**
  - Issues #16 and #17 carry "(Claude Code)" in their titles.
  - Every lane PR (#22, #24-#28) and PR #29 ends "Generated with Claude Code".
  - In the landing repo, all 7 of 7 commits carry a Claude `Co-Authored-By` line.
- **Links:** all 21 of 21 links in the README and posts return HTTP 200.

### Social posts

- **LinkedIn table (lines 40-53):** all 14 of the 14 page URLs match a link on that organisation's own site, fetched 2026-11-15.
  - The site checked for each: openmel.dev, elevenlabs.io, agenticdaysummit.com, mdc.edu, claude.com, anthropic.com, langchain.com, keenable.ai, ibm.com, pydantic.dev, fastapi.tiangolo.com, neon.com, render.com and vercel.com.
  - Luma lists Agentic Day's LinkedIn as `/in/agenticday-summit`, a personal-profile path. The post uses `/company/agenticday-summit`, which is the link on Agentic Day's own site, so the post is right.
- **X handles (lines 72 and 77):** all 15 of the 15 distinct handles match an official-site link, ignoring case. They are OpenMelDev, elevenlabs, agenticday, mdcollege, claudeai, LangChain, KeenableAI, IBMResearch (research.ibm.com), pydantic, fastapi, Gradio (gradio.app), litellm (litellm.ai), neondatabase, render and vercel.
- **Line 20, "first live run showed 24 of 24 claims 'verified', but some quotes didn't carry the claim's prices".**
  - `GET /api/runs/run-0e7ff2b1bb05` returned 24 claims, all 24 verified.
  - 3 of those claims (Mel Max, Warp Build, Warp Max) have prices missing from their quotes.
  - Issue #33's body agrees.
- **Line 20, "every number in a loosely matched quote must sit where the page has it".** `rules.py` docstring, lines 39-46.
- **Line 18, the plain-code verifier.** `rules.py` docstring, lines 1-14 and 93-96.
- **Line 22, the event credits.** Same evidence as the README's lines 531-534.
- **Line 83, the event details.** Match the Luma page.

### End card

- **Line 138, the tracks.** The Luma page lists "2. Agentic Marketing" and "8. Research, Productivity & Developer Agents".
- **Lines 136-137, the links.** Both return 200.
- **Lines 139-142, the credits.** Same evidence as the README's lines 531-548.

## Findings

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| 1 | README:529 (the photo) and posts:3: "the event photo cropped so that no attendee shows and the QR codes are blurred" | I4 ("is safe to publish" rests on one method) and data (AGENTS.md:67) | HIGH | The pixels are fine: no person shows, and the QR band is blurred. But `exif_tags.py` (exit 0) finds full EXIF in **both** files: Make and Model "Apple iPhone 17 Pro Max", capture time 2026:11:14 18:30:30 -05:00, and a GPS block with latitude, longitude, altitude, speed and direction. `gps_distance.py` (exit 0) puts the point about 70 m from the venue's Luma coordinates. I did not print the coordinates. `gh repo view` reports `visibility=PUBLIC`, and `git ls-remote origin refs/heads/jay/w3-readme-credits` returns `18caf71`, so the GPS-tagged JPEG is already public on that branch and on PR #50. Whether LinkedIn and X strip EXIF on upload was not checked. Not CRITICAL because no stated claim is false, and the location is the venue the post names. | Strip all metadata from both files (for example `ffmpeg -i in -map_metadata -1 out`, or `exiftool -all=`) and commit the clean JPEG. The old blob stays reachable on the pushed branch and PR ref; the owner decides whether that matters. |
| 2 | README:23 "Without the live keys (`ANTHROPIC_API_KEY`, `KEENABLE_API_KEY`) … the app replays one built-in demo run"; :55 "used when the live keys are not set"; :195-197 "With `ANTHROPIC_API_KEY` and `KEENABLE_API_KEY` set, the API and UI run the live service … Without them, they serve the built-in demo replay"; :364 "without the live keys, any subject and rival return the Acme vs Zeta demo battlecard" | I1 (contradicted by code and a re-run) | HIGH | `wiring.py:4-6`, `:107-118` and `:221-223` at `d719360` require **three** settings, including `DATABASE_URL`. `api_modes.py` (exit 0) shows: **D**, passcode and both keys but no `DATABASE_URL`: mode=demo, POST 202 `run-demo-0001`, Acme vs Zeta. **B**, passcode, no keys: POST **503** "KEENABLE_API_KEY is not set" (`routes.py:69`). **A**, no environment: POST **401**. Only the UI replays with no environment (`wiring.py:308-309`). | Name all three settings. Say the API returns 401 without a configured passcode and 503 without `KEENABLE_API_KEY`. Say the API replays the demo only when a passcode and the Keenable key are set but `ANTHROPIC_API_KEY` or `DATABASE_URL` is missing. |
| 3 | README:222 "every price, percentage, decimal or thousands number in the claim must also be in its quote"; posts:20 "Every price in a claim must be in its quote."; posts:74 "Now the verifier checks every price against its quote" | I1 (contradicted by a re-run) | HIGH | In `readme_examples.py` (exit 0), the claims "Pro costs 25 dollars a month.", "Pro costs 25 USD a month." and "Pro costs $ 25 a month." each verify (`quote_exact`) against the quote "Pro costs $20 a month". `rules.py` docstring lines 80-82 at `d719360` records this limit, and so does issue #45's first comment. | Say "every price written with a currency sign ($20, €5), every percentage, decimal or thousands number". In the posts, say "every $-price". |
| 4 | posts:31 "with every change gated by tests and a blind AI review" | I1 (contradicted) | HIGH | **Tests are gated:** the ruleset requires `gitleaks`, `leak-gate`, `dependency-audit`, `ci-python` and `api-image` (`gh api repos/JayR1031/receipts/rulesets/27284472`, exit 0). **Blind review is not:** ruleset 27284473 requires 0 approvals and no judge check (AGENTS.md:96). PR #35's body, line 111, says "Blind code review: **waived by the owner**", and the last code verdict, `verdicts/2026-11-15-gh33-r5.md`, reads `VERDICT: FAIL`. PR #31's body, line 1, says "PR #30 was merged before the verdict", and that verdict was FAIL. | Say "every change tested in CI; reviewed by a blind AI judge before merge, a rule the owner waived for two PRs". Or drop "gated" for the review. |
| 5 | posts:85 "No official event hashtag was confirmed." | I2 (no scope) | HIGH | The note names no place searched. I searched the Luma page, agenticdaysummit.com and openmel.dev with a hashtag regex (exit 0) and found none, so the claim holds where I looked. | Name the places searched, for example "none on the Luma page, agenticdaysummit.com or openmel.dev". |
| 6 | posts:57 "Mellea: it has no account of its own, so IBM is tagged." | I2 (no scope) | HIGH | No scope is given. My check: the mellea.ai home page links no LinkedIn or X account, and the `mellea-0.9.0` metadata links only docs.mellea.ai and GitHub. So the claim holds where I looked. | Say "mellea.ai and its PyPI page link no LinkedIn or X account". |
| 7 | README:20-21 "the deployed app runs live comparisons … A claim that fails gets up to two Mellea rewrites"; posts:20 "Claims that fail get up to two rewrites through Mellea's … loop" | I4 (pending on the deployed app) | MEDIUM | **Code:** at the deployed SHA (`d719360`, mode `live`), repairs are on by default (`wiring.py:133` and `:225`). **Runtime:** none on the deploy. The newest run in `/api/runs` started at 04:31:45Z, before #46 merged at 17:21:20Z. PR #46's body says "Not measured on the deployed app" and leaves Render's LiteLLM environment "Pending". | Start one live run on Render and cite its run id and its `claim repair: pricing failing=N repaired=M` log line. Until then, say repairs are pending on the deployed app. |
| 8 | posts:74 "and Mellea repairs what fails" | I1 / I4 (overstated) | MEDIUM | Repairs are at most two attempts (`repair.py:10-13`), not a guarantee. In `run-a7be7a53cba9`, at least 6 of the 8 verified pricing claims carry a plan name their quote lacks (`mellea/live_repaired.out:5-16`; issue #45). | Say "Mellea gets up to two rewrites for claims that fail; the verifier re-checks them". |
| 9 | README:495 "in a separate repairs-off run, every failure was a claim price not in its quote" | Numbers / I1 | MEDIUM | The run is not named and the denominator is missing. It is `run-3cc9b768f440`: 5 of 5 failures, 15 of 20 verified (`mellea/live_reasons.out:1-6`). The heading "Why claims failed" sits next to the table, but PR #46's body says these reasons "are not a measured cause for those 28 failures". | Name the run, say "5 of 5 failures, in a run with 15 of 20 verified", and say the table runs did not record their failure reasons. |
| 10 | README:496 "In one repairs-on run, at least 6 of the 8 verified pricing claims did." | I1 | MEDIUM | This run is not in the table, and the README does not say which run it is. It is `run-a7be7a53cba9`, 20 of 20 verified (`live_repaired.out:17`); 7 of its 8 verified pricing claims are rewrites. | Name `run-a7be7a53cba9` and say it is not one of the four table runs. |
| 11 | README:490 and :492 "22 / 22" (repairs on) | I6 (a known false positive is not excluded or stated) | MEDIUM | Issue #45 (last comment, item 2) and PR #46 record that a repair can duplicate another claim's receipt, which inflates verified/total. The pair script records counts only (`live_pairs.py:62-69`), so duplicates in these runs were not measured. | Add a bullet: "verified/total can count a repaired claim that duplicates another's receipt (issue #45); not measured in these runs". |
| 12 | README:485-492, the four live runs | I6 (cannot be re-run) | MEDIUM | The scripts exist only in a session scratchpad (`…/scratchpad/mellea/live_pairs.py`, `live_reasons.py`, `live_repaired.py`), which a reboot can clear. PR #46's body says "Scripts: three, in session scratch only". | Commit the scripts (for example under `scripts/`) or quote the command, environment and expected output in the README. |
| 13 | README:225 "The rules have known limits, tracked in issue #45. Plan labels… Bare-integer counts… A quote whose page text runs past the score window…" | Scope (the list is incomplete) | MEDIUM | The list leaves out three fail-open limits recorded in `rules.py`'s docstring at `d719360`: unsigned claim prices (lines 80-82; finding 3); any standalone "free" matching `$0` (lines 84-87; the case "Pro is $0 and $20." on the quote "Pro is not free: it costs $20." verifies `quote_exact`); and values swapped inside one quote (lines 91-92; the claim "Pro is $19 yearly and $199 monthly." on the quote "Pro yearly: $199. Pro monthly: $19." verifies). | List all six limits, or say "among them" and link to the docstring. |
| 14 | posts:3 "the demo video `receipts-demo-narrated-v2.mp4`, whose end card now credits everyone" | I1 (contradicted) | MEDIUM | The end card (`index.html:139`, and the frame at 116 s) credits Mel × ElevenLabs and Miami Dade College but not **Agentic Day**. Posts:22 and README:533 both credit Agentic Day as organiser. | Add "organised by Agentic Day" to `#s7-e` and re-render, or drop "credits everyone". |
| 15 | README:306-307 "This is the live failure that issue #33 reported." | I1 (precision) | LOW | The claim and quote are verbatim from `run-0e7ff2b1bb05` (`GET /api/runs/run-0e7ff2b1bb05`, 200, where it was verified `quote_exact`), the run issue #33 reports. But issue #33's body quotes the Mel Max claim, and the README's page line is the test's invented page (`tests/test_verify_claim_numbers.py:6-10`, `:62`). | Say "the claim and quote come from the run issue #33 reported (`run-0e7ff2b1bb05`); the page text is invented for the test". |
| 16 | README:227-228 "the same cases are in `tests/test_verify.py` and `tests/test_verify_claim_numbers.py`" | I1 | LOW | 6 of the 7 example inputs appear verbatim in the tests. The markdown case differs: `test_verify.py:31-32` uses a different link URL and a blank line, compared with README:287-288. The README's version still reproduces. | Say "the same cases or close variants". |
| 17 | README:548 "Claude Code built Wave 0 and lanes L1 to L5" | Record consistency | LOW | The README is right: issue #17's title says "(Claude Code)", and PR #26 ends "Generated with Claude Code". But ADR-0004:29 at `d719360` still says Mel "Builds lane L5 (`ui/`)". | Correct ADR-0004's Mel row in a separate PR. |
| 18 | README:529 and posts:3 "the QR codes are blurred" | I4 (one method) | LOW | Visually confirmed: `qr-band-zoom.png` at 3× shows a smooth blur with no module pattern. A decoder check is pending because `which zbarimg` found nothing. | Run a QR decoder on both files and record "no symbol found". |
| 19 | README:531-534, posts:22, posts:72 and the end card credit Agentic Day, Mel × ElevenLabs and MDC | Completeness | LOW | The Luma page's hosts list also has Miami Fintech Club and The AI Collective. Leaving them out is not false. | The owner decides whether to credit the co-hosts. |

VERDICT: FAIL
