# Brief for Mel: GitHub issue #48, close the theme-test gaps left by #40

**Read `AGENTS.md` first.** This is lane L5 (the UI) again. The work is all in the tests: four small gaps the blind judge left after #40 (PR #47, which you built).

## Where to work
- **Folder:** `/Users/jay/Projects/receipts/.worktrees/ui-gaps`. It is a git worktree on branch `jay/gh-48-ui-test-gaps`, cut from `origin/main` at `b526a14`. Work only there.
- **Files you may change:** `tests/test_ui_theme.py` and `tests/test_ui_render.py`. Change `src/receipts/ui/**` only if a test proves the app itself is wrong; if that happens, stop and say so first.
- **Do not touch:** any screenshot (`docs/assets/**`), any frozen file (`src/receipts/contracts.py`, `src/receipts/settings.py`, `src/receipts/fakes/**`, `tests/conftest.py`, `pyproject.toml`, `uv.lock`), or anything outside the two test files.

## The four gaps
1. **The named-colour test flags ordinary words.** `test_theme_colours_have_no_named_tokens_and_no_hsl_or_hsla` (`tests/test_ui_theme.py`, around line 343) matches *every* word in the CSS against the colour-name list, so a legitimate `white-space: pre-wrap` fails with "found: ['white']".
   - **Fix:** check only the *values* of colour-bearing declarations: the text after `:` up to `;` or `}` for properties such as `color`, `background`, `background-color`, `border`, `border-color`, `outline`, `outline-color`, `fill`, `stroke` and `box-shadow`. Also check each theme value on its own (that part already works).
   - **Tests:** `.x { white-space: pre-wrap; }` must pass, and `.x { color: white; }` and `.x { background: orange; }` must fail.
2. **Colour functions the guard misses.** `oklch()`, `hwb()` and upper-case `RGB()` pass today.
   - **Fix:** ban every non-hex colour function except greyscale `rgb()`/`rgba()`, matched case-insensitively: `hsl`, `hsla`, `hwb`, `lab`, `lch`, `oklab`, `oklch` and `color(`. Make the `rgb()` grey check case-insensitive too (`RGB(255, 0, 0)` must fail).
   - **Tests:** one failing case each, for `oklch(0.7 0.2 30)`, `hwb(0 0% 0%)` and `RGB(255, 0, 0)`.
3. **The progress-log guard only knows `<span`.** In `test_render_event_line_is_kind_specific_for_every_kind` (`tests/test_ui_render.py`, around line 38), replace the `"<span" not in line` check with a check that the line contains no HTML tag at all, for example the regex `<\s*/?\s*[A-Za-z]`. Also check the real event lines still pass. The sample events contain no `<`, so they should.
4. **Tidy-up.** Delete the unused `HEX` constant (`tests/test_ui_theme.py`, around line 28). Keep one of the two 3-to-6-digit hex helpers (`_expand_hex_colour`, `_expand_3_to_6_hex`) and use it everywhere.

## How to work (what the reviewer will check)
1. **Baseline first:** the worktree is new and has no environment yet, so run `uv sync` in it first. Then remove `__pycache__` outside `.venv`, run `bin/jig` and `uv run pytest -q -m "not integration"`, and note the counts.
2. **Test-first, for each gap:**
   - Write the failing test first. Run it against the *current* code and save the command, its exit code and the failing test names. That is the red run, and the reviewer checks one exists for every new test.
   - Then fix the test logic until it passes.
3. **Sabotage each new guard once:**
   - Temporarily put the defect it should catch into `src/receipts/ui/theme.py` or `render.py` (for example, add `.x { color: oklch(0.7 0.2 30); }` to `CSS`). Then run the tests and confirm the right test goes red. Then restore the file.
   - **The sabotage must not break the import.** Before trusting a red, run `uv run --no-sync python -c "import receipts.ui.app, receipts.ui.render, receipts.ui.theme"` and confirm exit 0. A red caused by a syntax error proves nothing.
   - Record the command, exit code and red test for each.
4. **Gates:** remove `__pycache__` outside `.venv`, `bin/jig` must exit 0, and report the `pytest -m "not integration"` counts and any skip by name.
5. **Commit and push:** commit as `gh-48: ui: …` and run `git push -u origin jay/gh-48-ui-test-gaps`. Do not open the PR and do not merge; Claude Code runs the blind judge.

## Report back
- The head SHA and the files changed.
- **One line per new or changed test:** its red run (command, exit code, failing test).
- **One line per guard:** the sabotage (what you broke, the import check's exit code, and the test that went red).
- The gate results, with counts.
- Anything you could not do, and why.
