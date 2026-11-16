# Brief for Mel: GitHub issue #40, battlecard status colours and tighter theme tests

> **Correction, 2026-11-15 (coordinating session):** item 5 below wrongly said to retake every `docs/assets/ui-theme-*.png`. Only screenshots that showed the old tagline were in scope. `ui-theme-before.png` (the pre-#34 theme) and `ui-theme-landing.png` (the landing site) must match `main`; both were restored on the branch.

**Read `AGENTS.md` first; it is the standard.** This task is in lane L5 (the UI), which you built.

## Where to work
- **Folder:** `/Users/jay/Projects/receipts/.worktrees/ui-status`. It is a git worktree on branch `jay/gh-40-ui-status`, cut from `origin/main` at `b8ed8d6`. Work only in this folder.
- **Files you may change:**
  - `src/receipts/ui/**`
  - `tests/test_ui_app.py`, `tests/test_ui_render.py`, `tests/test_ui_theme.py`
  - `docs/assets/ui-theme-*.png`
- **Everything else is out of scope.** That includes the frozen files: `src/receipts/contracts.py`, `src/receipts/settings.py`, `src/receipts/fakes/**`, `tests/conftest.py`, `pyproject.toml` and `uv.lock`. If you need one of them changed, stop and say so.

## What to do (from issue #40, the round-2 judge's LOW findings on the UI theme PR)
1. **Status colours.** `src/receipts/ui/render.py` `_render_claim` writes plain `[verified]` / `[unverified]`, so the theme's `.status-verified` (emerald-400) and `.status-dropped` (red-400) classes never show. Wrap each status mark in the matching class:
   - verified → `status-verified`
   - unverified → `status-dropped`

   Check that Gradio's Markdown component keeps the `class` attribute. If it strips it, say so and propose another way.
2. **Fonts.** The font test checks only the font list. Also assert that `CSS` contains no `@import` and no `url(http`, so a Google Fonts import or a `fonts.gstatic.com` `@font-face` would fail it.
3. **Tagline and contrast.**
   - Pin `TAGLINE == "Every claim carries a receipt."`.
   - Add a WCAG contrast test (relative luminance, ratio of at least 4.5:1 for text) for the grey text colour and the focus border, each against the `#000` background.
4. **The colour test.** It misses 3-digit hex, named colours and `hsl()`; extend it to catch each. Also make the theme/CSS wiring test fail if `mount_ui` drops `theme=` or `css=`.
5. **Screenshots.** Retake `docs/assets/ui-theme-*.png` at your final commit. Run the app with `uv run uvicorn receipts.api.app:app --port 8000`, then open http://127.0.0.1:8000. With no environment set it runs in demo mode, which is fine for screenshots. The current images show the old tagline.

**Brand rule:** monochrome, as on the landing page. Colour is used only for status, small: emerald-400 for verified, red-400 for dropped or unverified.

## How to work
- **TDD.** Write each failing test first and run it. Save the red output (the command, its exit code and the failing test names) and paste it in your final report. Then implement.
- **Sabotage each new guard once:** break the code it protects, confirm a test goes red, restore it, confirm green. List each in your report.
- **Gates, all of which must pass:**
  - Remove `__pycache__` outside `.venv` first.
  - `bin/jig` exits 0.
  - `uv run pytest -q -m "not integration"`: report the passed and deselected counts, and name any skip.
- **Commit** with a message starting `gh-40: ui: ` and push the branch: `git push -u origin jay/gh-40-ui-status`.
- **Do not open the PR and do not merge.** Tell Jay when you've pushed. Claude Code then runs the blind judge and opens the PR.

## Report back
- The branch head SHA.
- The files changed.
- The red runs.
- The sabotage list.
- The gate results with counts.
- Anything you could not do, and why.
