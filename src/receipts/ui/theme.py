# pyright: basic
"""The UI's look: a monochrome dark theme, the CSS it cannot reach, and the header (lane L5).

The values are measured from the landing page (the `receipts-landing` repository:
`app/globals.css`, `app/layout.tsx`, `components/hero.tsx`, `navbar.tsx`, `features.tsx`,
`receipt-preview.tsx`) so the app and the site read as one product: a pure black page,
near-black surfaces, hairline white/10 borders, Inter, and a white primary button. The only
colours are the two status colours, used small, as the landing page uses them.

Every variable is set for light and dark mode alike, so the app looks the same whichever mode
the browser asks for. CSS covers only what Gradio's theme variables do not reach.

The logo is read once at import from the package's own assets with `importlib.resources`, so it
ships wherever the package does (the Docker image copies `src/`), and is inlined as a data URI
so the page needs no extra route for it.
"""

from __future__ import annotations

import base64
from importlib.resources import files

from gradio.themes import Base as BaseTheme
from gradio.themes import Font
from gradio.themes.utils.colors import Color

LANDING_URL = "https://receipts-landing-nine.vercel.app"
TAGLINE = "Every claim carries a receipt."
LOGO_ALT = "Receipts"
# The asset is 640x144 (white on transparent); shown 32px tall, so about 142px wide.
LOGO_HEIGHT_PX = 32
LOGO_WIDTH_PX = 142

# Palette, by the Tailwind names the landing page uses.
BLACK = "#000000"  # page background (globals.css --background)
WHITE = "#ffffff"
SURFACE = "#0a0a0a"  # neutral-950: blocks (receipt-preview panel)
SURFACE_2 = "#151515"  # inputs and table rows (button.tsx base fill)
RAISED = "#1f1f1f"  # raised and selected elements
TEXT = "#fafafa"  # globals.css --foreground
TEXT_SECONDARY = "#a3a3a3"  # neutral-400
BORDER = "rgba(255, 255, 255, 0.10)"  # border-white/10
BORDER_FOCUS = "#a3a3a3"
HOVER_FILL = "#e5e5e5"  # primary button hover (neutral-200)
SUBTLE_FILL = "rgba(255, 255, 255, 0.05)"  # secondary button hover
VERIFIED = "#34d399"  # emerald-400, status only
DROPPED = "#f87171"  # red-400, status only
RADIUS = "0.5rem"  # globals.css --radius
RADIUS_INPUT = "calc(0.5rem - 2px)"  # --radius-md

# One grey ramp for every hue Gradio derives colours from, so no default accent (Gradio's
# emerald, blue or zinc) can leak into a component this file does not name.
MONO = Color(
    name="receipts_mono",
    c50="#fafafa",
    c100="#f5f5f5",
    c200="#e5e5e5",
    c300="#d4d4d4",
    c400="#a3a3a3",
    c500="#737373",
    c600="#525252",
    c700="#404040",
    c800="#262626",
    c900="#171717",
    c950="#0a0a0a",
)

# Set identically on the light variable and its `_dark` twin.
_BOTH_MODES: dict[str, str] = {
    "body_background_fill": BLACK,
    "body_text_color": TEXT,
    "body_text_color_subdued": TEXT_SECONDARY,
    "background_fill_primary": BLACK,
    "background_fill_secondary": SURFACE,
    "border_color_primary": BORDER,
    "border_color_accent": BORDER_FOCUS,
    "border_color_accent_subdued": BORDER,
    "color_accent_soft": RAISED,
    "link_text_color": TEXT,
    "link_text_color_active": TEXT,
    "link_text_color_hover": TEXT_SECONDARY,
    "link_text_color_visited": TEXT,
    "code_background_fill": RAISED,
    "block_background_fill": SURFACE,
    "block_border_color": BORDER,
    "block_border_width": "1px",
    "block_info_text_color": TEXT_SECONDARY,
    "block_label_background_fill": SURFACE,
    "block_label_border_color": BORDER,
    "block_label_text_color": TEXT_SECONDARY,
    "block_title_text_color": TEXT_SECONDARY,
    "block_shadow": "none",
    "panel_background_fill": SURFACE,
    "panel_border_color": BORDER,
    "accordion_text_color": TEXT,
    "input_background_fill": SURFACE_2,
    "input_background_fill_hover": SURFACE_2,
    "input_background_fill_focus": SURFACE_2,
    "input_border_color": BORDER,
    "input_border_color_hover": BORDER_FOCUS,
    "input_border_color_focus": BORDER_FOCUS,
    "input_border_width": "1px",
    "input_placeholder_color": TEXT_SECONDARY,
    "input_shadow": "none",
    "input_shadow_focus": "none",
    "loader_color": TEXT_SECONDARY,
    "slider_color": TEXT,
    "stat_background_fill": RAISED,
    "table_border_color": BORDER,
    "table_even_background_fill": SURFACE,
    "table_odd_background_fill": SURFACE_2,
    "table_row_focus": RAISED,
    "table_text_color": TEXT,
    "error_background_fill": SURFACE,
    "error_border_color": DROPPED,
    "error_icon_color": DROPPED,
    "error_text_color": TEXT,
    "button_border_width": "1px",
    "button_primary_background_fill": WHITE,
    "button_primary_background_fill_hover": HOVER_FILL,
    "button_primary_border_color": WHITE,
    "button_primary_border_color_hover": HOVER_FILL,
    "button_primary_text_color": BLACK,
    "button_primary_text_color_hover": BLACK,
    "button_primary_shadow": "none",
    "button_primary_shadow_hover": "none",
    "button_primary_shadow_active": "none",
    "button_secondary_background_fill": "transparent",
    "button_secondary_background_fill_hover": SUBTLE_FILL,
    "button_secondary_border_color": BORDER,
    "button_secondary_border_color_hover": BORDER_FOCUS,
    "button_secondary_text_color": TEXT,
    "button_secondary_text_color_hover": TEXT,
    "button_secondary_shadow": "none",
    "button_cancel_text_color_hover": TEXT,
    # Unused by the app today, but Gradio's defaults differ by mode; pinned so none can.
    "checkbox_background_color": SURFACE_2,
    "checkbox_border_color": BORDER,
    "checkbox_border_color_hover": BORDER_FOCUS,
    "shadow_spread": "1px",
}

# Variables with no `_dark` twin in Gradio 6.32.
_ANY_MODE: dict[str, str] = {
    "color_accent": TEXT,
    "block_radius": RADIUS,
    "block_label_text_weight": "500",
    "block_title_text_weight": "500",
    "container_radius": RADIUS,
    "embed_radius": RADIUS,
    "input_radius": RADIUS_INPUT,
    "table_radius": RADIUS,
    "button_large_radius": RADIUS,
    "button_medium_radius": RADIUS,
    "button_small_radius": RADIUS,
    "button_large_text_weight": "600",
    "button_medium_text_weight": "600",
    "button_transition": "background-color 0.2s ease, border-color 0.2s ease",
    "prose_header_text_weight": "600",
}


def _both_modes(values: dict[str, str]) -> dict[str, str]:
    return {name: value for key, value in values.items() for name in (key, f"{key}_dark")}


THEME = BaseTheme(
    primary_hue=MONO,
    secondary_hue=MONO,
    neutral_hue=MONO,
    # Plain family names: nothing is fetched from Google or any other host (ADR-0004). Inter is
    # used where installed; otherwise the OS UI font, which is close to it.
    font=(Font("Inter"), "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"),
    font_mono=(Font("JetBrains Mono"), "ui-monospace", "SFMono-Regular", "Menlo", "monospace"),
).set(**_both_modes(_BOTH_MODES), **_ANY_MODE)

FORM_CSS = f"""
/* The account line, the tabs and the Run form (app.py `_run_form`), in the battlecard's
   language: one card, a mono eyebrow, a bold heading, quiet labels. */
/* On wide screens the account line is taken out of flow and sat on the tab row, right of
   the tabs. Clicks pass through the empty box; the link and Sign out keep theirs. */
#account {{ position: relative; z-index: 2; height: 0; margin: 0; overflow: visible;
  pointer-events: none; }}
#account .prose {{
  position: absolute; right: 0; top: 0; height: 43px;
  display: flex; align-items: center; justify-content: flex-end;
}}
.receipts-account {{
  display: inline-flex; align-items: center; justify-content: flex-end; gap: 12px;
  flex-wrap: wrap; pointer-events: auto; min-height: 43px;
}}
.receipts-account form {{ margin: 0; }}
.receipts-account-text {{
  display: inline-flex; align-items: center; gap: 8px; font-family: var(--font-mono);
  font-size: 0.75rem; letter-spacing: 0.02em; color: {TEXT_SECONDARY};
}}
.receipts-account-text::before {{
  content: ""; flex: none; width: 6px; height: 6px; border-radius: 9999px;
  background: {TEXT_SECONDARY};
}}
button.receipts-about {{
  background: transparent; cursor: pointer; font-family: inherit; line-height: 1.25rem;
}}
.tabs > .tab-wrapper {{ height: auto; padding-bottom: 0; margin-bottom: 20px; }}
.tab-container:not(.visually-hidden) {{
  width: auto; height: auto; gap: 4px; padding: 4px; border: 1px solid {BORDER};
  border-radius: 9999px; background: {SURFACE};
}}
.tab-container::after, .tab-container button::after {{ display: none !important; }}
.tab-container button {{
  height: auto !important; padding: 6px 18px !important; border-radius: 9999px;
  color: {TEXT_SECONDARY}; font-size: 0.875rem; font-weight: 500;
  transition: color 0.2s ease, background-color 0.2s ease;
}}
.tab-container button.selected {{ background: {RAISED}; color: {TEXT}; }}
.tab-container button:hover:not(.selected) {{ background: transparent !important; }}
.rf {{
  background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
  padding: 28px; gap: 22px;
}}
.rf .block, .rf .form {{
  background: transparent !important; border: 0 !important; padding: 0 !important;
  box-shadow: none !important;
}}
.rf .form {{ gap: 16px; overflow: visible; }}
.rf .row {{ gap: 16px; }}
.rf-head .prose {{ display: flex; flex-direction: column; gap: 10px; }}
.rf-head :is(p, h2) {{ margin: 0 !important; }}
.rf-head p:first-of-type {{
  font-family: var(--font-mono); font-size: 0.75rem; letter-spacing: 0.04em;
  text-transform: uppercase; color: {TEXT_SECONDARY};
}}
.rf-head h2 {{ font-size: 1.5rem !important; line-height: 1.25; font-weight: 600; }}
.rf-head p:last-of-type {{
  max-width: 560px; color: {TEXT_SECONDARY}; font-size: 0.875rem; line-height: 1.4rem;
}}
.rf label > span:first-child {{
  margin-bottom: 8px; color: {TEXT_SECONDARY}; font-size: 0.8125rem; font-weight: 500;
}}
.rf :is(textarea, input) {{ padding: 10px 14px !important; font-size: 0.9375rem !important; }}
.rf-pair {{ flex-wrap: nowrap !important; align-items: flex-end; }}
.rf-pair > .form {{ flex: 1 1 0 !important; }}
.rf-vs {{
  flex: none !important; width: auto !important; min-width: 1.75rem !important;
  min-height: 1.5rem !important; height: auto !important; overflow: visible !important;
  align-self: flex-end;
}}
.rf-vs p {{
  margin: 0 !important; padding-bottom: 11px; font-family: var(--font-mono);
  font-size: 0.8125rem; color: {TEXT_SECONDARY};
}}
.rf-extra {{ padding-top: 20px; border-top: 1px solid {BORDER}; }}
.rf-extra label > span:first-child {{ font-size: 0.75rem; }}
.rf-extra :is(textarea, input) {{ font-size: 0.875rem !important; }}
.rf-foot {{ align-items: center; justify-content: space-between; flex-wrap: nowrap; }}
.rf-hint {{ min-width: 0 !important; }}
.rf-hint p {{ margin: 0 !important; color: {TEXT_SECONDARY}; font-size: 0.8125rem; }}
#start {{
  flex: none; min-width: 148px; height: 40px; padding: 0 22px; border-radius: {RADIUS};
  font-size: 0.875rem;
}}
#refresh {{ align-self: flex-end; flex: none; width: auto; min-width: 0; padding: 4px 14px; }}
#start:disabled {{
  background: {RAISED}; border-color: {BORDER}; color: {TEXT_SECONDARY}; cursor: progress;
  opacity: 1;
}}
#start:disabled::before {{
  content: ""; width: 6px; height: 6px; margin-right: 10px; border-radius: 9999px;
  background: {TEXT_SECONDARY}; animation: rf-pulse 1.2s ease-in-out infinite;
}}
@keyframes rf-pulse {{ 50% {{ opacity: 0.3; }} }}
@media (max-width: 640px) {{
  #account {{ height: auto; overflow: visible; }}
  #account .prose {{
    position: static; height: auto; min-height: 0; justify-content: flex-start;
  }}
  .receipts-account {{ justify-content: space-between; width: 100%; min-height: 0; }}
  .receipts-account-text {{ font-size: 0.6875rem; }}
  .rf {{ padding: 20px; }}
  .rf-head h2 {{ font-size: 1.25rem !important; }}
  .rf-pair, .rf-extra {{ flex-direction: column; align-items: stretch; }}
  .rf .row.rf-pair {{ gap: 6px; }}
  .rf-vs {{ display: none; }}
  .rf-foot {{ flex-direction: column-reverse; align-items: stretch; gap: 12px; }}
  #start {{ width: 100% !important; }}
  .rf-hint p {{ text-align: center; }}
}}
"""

BATTLECARD_CSS = f"""
/* The battlecard (render.py), shared by the app and the public share page (share.py). */
.bc {{ display: flex; flex-direction: column; gap: 28px; color: {TEXT}; }}
.bc-head {{ display: flex; flex-direction: column; gap: 10px; }}
.bc-eyebrow, .bc-method, .bc-domain-count {{
  font-family: var(--font-mono); font-size: 0.75rem; letter-spacing: 0.04em;
  color: {TEXT_SECONDARY}; margin: 0;
}}
.bc-eyebrow {{ text-transform: uppercase; }}
.bc-domain-count {{ flex: none; font-weight: 400; }}
.bc-title {{ margin: 0; font-size: 1.75rem; line-height: 1.2; font-weight: 600; }}
.bc-vs {{ color: {TEXT_SECONDARY}; font-weight: 400; }}
.bc-score {{ display: flex; align-items: baseline; gap: 10px; margin-top: 6px; }}
.bc-score-num {{ font-size: 2.5rem; line-height: 1; font-weight: 600; letter-spacing: -0.02em; }}
.bc-score-of {{ color: {TEXT_SECONDARY}; font-weight: 400; }}
.bc-score-label {{ color: {TEXT_SECONDARY}; font-size: 0.875rem; }}
.bc-meter {{
  height: 4px; border-radius: 9999px; overflow: hidden; max-width: 420px;
  background: {RAISED};
}}
.bc-meter-fill {{ display: block; height: 100%; background: {VERIFIED}; }}
.bc-meta {{ margin: 0; color: {TEXT_SECONDARY}; font-size: 0.8125rem; }}
.bc-share {{
  align-self: flex-start; color: {TEXT} !important; font-size: 0.8125rem;
  text-decoration: none !important; padding: 4px 12px; border: 1px solid {BORDER};
  border-radius: 9999px;
}}
.bc-share:hover {{ border-color: {BORDER_FOCUS}; }}
.bc-domain {{ display: flex; flex-direction: column; gap: 10px; }}
.bc-domain-title {{
  display: flex; align-items: baseline; justify-content: space-between; gap: 12px;
  padding-bottom: 10px; border-bottom: 1px solid {BORDER};
  font-size: 1rem; font-weight: 600;
}}
.bc-claim {{
  display: flex; flex-direction: column; gap: 10px; padding: 16px 18px;
  background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: {RADIUS};
}}
.bc-claim-row {{ display: flex; align-items: flex-start; gap: 12px; }}
.bc-mark {{ flex: none; width: 18px; font-weight: 700; line-height: 1.5rem; text-align: center; }}
.bc-claim-text {{ flex: 1; margin: 0; line-height: 1.5rem; }}
.bc-about {{
  flex: none; font-size: 0.75rem; color: {TEXT_SECONDARY}; padding: 2px 10px;
  border: 1px solid {BORDER}; border-radius: 9999px;
}}
/* Gradio's prose styles space out p, h2, h3 and blockquote; the card sets its own. */
.bc :is(p, h2, h3, blockquote) {{ margin: 0 !important; }}
.bc-quote {{
  padding: 2px 0 2px 14px !important; border-left: 2px solid {BORDER_FOCUS} !important;
  color: {TEXT_SECONDARY}; font-size: 0.875rem; line-height: 1.4rem; font-style: normal;
}}
.bc-quote, .bc-source, .bc-why {{ margin-left: 30px !important; }}
.bc-source, .bc-why, .bc-search {{ font-size: 0.8125rem; color: {TEXT_SECONDARY} !important; }}
.bc-url {{
  color: {TEXT} !important; padding: 0 !important; text-decoration: underline;
  text-underline-offset: 3px;
}}
a.bc-url:hover {{ color: {TEXT_SECONDARY} !important; }}
.bc-claim-dropped {{ background: {SURFACE}; }}
.bc-claim-dropped .bc-claim-text {{ color: {TEXT_SECONDARY}; }}
.bc-dropped {{ display: flex; flex-direction: column; gap: 10px; }}
.bc-dropped > summary {{
  cursor: pointer; color: {TEXT_SECONDARY}; font-size: 0.875rem; padding: 6px 0;
}}
.bc-dropped > summary:hover {{ color: {TEXT}; }}
.bc-dropped[open] > summary {{ margin-bottom: 10px; }}
.bc-empty {{ margin: 0; color: {TEXT_SECONDARY}; }}
@media (max-width: 640px) {{
  .bc-claim-row {{ flex-wrap: wrap; }}
  .bc-claim-text {{ flex: 1 1 calc(100% - 30px); }}
  .bc-about {{ margin-left: 30px; }}
  .bc-quote, .bc-source, .bc-why {{ margin-left: 0 !important; }}
}}
/* The only colours, for status marks; render.py wraps battlecard status marks in these classes. */
.status-verified {{ color: {VERIFIED}; }}
.status-dropped {{ color: {DROPPED}; }}
"""

PROGRESS_CSS = f"""
/* The live progress view (render.py `render_progress`): one lane per domain, then a one-line
   summary once the run is done. Listed before the battlecard so its status classes win. */
#run-view {{ padding: 0 !important; border: 0 !important; background: transparent !important; }}
#run-view:has(.rp) {{
  background: {SURFACE} !important; border: 1px solid {BORDER} !important;
  border-radius: 12px; padding: 28px !important; overflow: hidden;
}}
.rp {{ display: flex; flex-direction: column; gap: 20px; color: {TEXT}; }}
/* Lanes are <li class="rp-lane">; excluding them keeps the claim-card padding. */
.rp :is(p, h2, h3, ol, ul, li):not(.rp-lane) {{
  margin: 0 !important; padding: 0 !important; list-style: none !important;
}}
.rp-head {{ display: flex; flex-direction: column; gap: 10px; }}
.rp-top {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
.rp-eyebrow, .rp-clock, .rp-lane-status, .rp-count {{
  font-family: var(--font-mono); font-size: 0.75rem; letter-spacing: 0.04em;
  color: {TEXT_SECONDARY};
}}
.rp-eyebrow {{ display: flex; align-items: center; gap: 8px; text-transform: uppercase; }}
.rp-dot {{ flex: none; width: 8px; height: 8px; border-radius: 9999px; background: {TEXT}; }}
.rp-done .rp-dot {{ background: {VERIFIED}; }}
.rp-title {{ font-size: 1.375rem; line-height: 1.25; font-weight: 600; }}
.rp-vs {{ color: {TEXT_SECONDARY}; font-weight: 400; }}
.rp-meter {{ height: 4px; border-radius: 9999px; overflow: hidden; background: {RAISED}; }}
.rp-meter-fill {{ display: block; height: 100%; background: {TEXT}; transition: width 0.4s ease; }}
.rp-done .rp-meter-fill {{ background: {VERIFIED}; }}
.rp-meta, .rp-error, .rp-notice-text {{ color: {TEXT_SECONDARY}; font-size: 0.8125rem; }}
.rp-done {{ gap: 10px; }}
.rp-lanes {{ display: flex; flex-direction: column; gap: 10px; }}
.rp-lane {{
  display: grid; grid-template-columns: 180px minmax(0, 1fr); column-gap: 24px; row-gap: 10px;
  padding: 16px 18px !important; background: {SURFACE_2}; border: 1px solid {BORDER};
  border-radius: {RADIUS};
}}
#run-view .rp-lane {{ padding: 16px 18px !important; }}
.rp-lane-head {{ grid-row: 1 / span 3; display: flex; flex-direction: column; gap: 6px; }}
.rp-lane-title {{ font-size: 0.9375rem; font-weight: 600; }}
.rp-lane-queued {{ background: {SURFACE}; }}
.rp-lane-queued .rp-lane-title {{ color: {TEXT_SECONDARY}; }}
.rp-steps {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; }}
.rp-step {{
  display: flex; flex-direction: column; gap: 6px; font-size: 0.75rem; color: {TEXT_SECONDARY};
}}
.rp-step::before {{
  content: ""; display: block; height: 4px; border-radius: 9999px; background: {RAISED};
}}
.rp-step-done::before {{ background: {TEXT}; }}
.rp-step-current {{ color: {TEXT}; }}
.rp-step-current::before {{ background: {TEXT_SECONDARY}; }}
.rp-running .rp-dot, .rp-running .rp-step-current::before {{
  animation: rp-pulse 1.4s ease-in-out infinite;
}}
.rp-lane-error .rp-step-current::before {{ background: {DROPPED}; animation: none; }}
.rp-counts {{ display: flex; flex-wrap: wrap; gap: 4px 16px; }}
.rp-count-num {{ color: {TEXT}; font-weight: 600; }}
.rp-activity {{
  font-size: 0.8125rem; color: {TEXT_SECONDARY}; overflow: hidden;
  display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 1; line-clamp: 1;
}}
@keyframes rp-pulse {{ 50% {{ opacity: 0.35; }} }}
@media (prefers-reduced-motion: reduce) {{
  .rp-running .rp-dot, .rp-running .rp-step-current::before {{ animation: none; }}
}}
.rp-log {{
  background: transparent !important; border: 1px solid {BORDER} !important;
  border-radius: {RADIUS};
}}
@media (max-width: 640px) {{
  #run-view:has(.rp) {{ padding: 20px !important; }}
  .rp-lane {{ grid-template-columns: minmax(0, 1fr); }}
  .rp-lane-head {{
    grid-row: auto; flex-direction: row; align-items: baseline; justify-content: space-between;
  }}
  .rp-activity {{ -webkit-line-clamp: 2; line-clamp: 2; }}
}}
"""

CSS = f"""
/* Gradio's body is a flex column, so an auto-margined container shrinks to its widest child. */
.gradio-container {{ width: 100%; max-width: 1100px !important; margin: 0 auto; }}
gradio-app {{
  background: radial-gradient(50% 320px at 50% 0%, rgba(255, 255, 255, 0.05), transparent)
    no-repeat, {BLACK} !important;
}}
.block:has(.receipts-header) {{ width: 100%; margin-left: 0; margin-right: 0; }}
.receipts-header {{
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 20px 0 12px;
}}
.receipts-brand {{ display: flex; align-items: center; gap: 16px; min-width: 0; }}
.receipts-brand img {{ height: {LOGO_HEIGHT_PX}px; width: auto; display: block; }}
.receipts-tagline {{
  margin: 0; padding-left: 16px; border-left: 1px solid {BORDER};
  color: {TEXT_SECONDARY}; font-size: 0.875rem; line-height: 1.25rem;
}}
@media (max-width: 640px) {{
  .receipts-brand {{ flex-direction: column; align-items: flex-start; gap: 6px; }}
  .receipts-tagline {{ border-left: 0; padding-left: 0; }}
}}
.receipts-about {{
  color: {TEXT_SECONDARY} !important; font-size: 0.875rem; text-decoration: none !important;
  padding: 6px 14px; border: 1px solid {BORDER}; border-radius: 9999px;
  transition: color 0.2s ease, border-color 0.2s ease;
}}
.receipts-about:hover {{ color: {TEXT} !important; border-color: {BORDER_FOCUS}; }}
{FORM_CSS}
#progress textarea {{
  font-family: var(--font-mono); font-size: 0.8125rem; line-height: 1.6; color: {TEXT_SECONDARY};
}}
/* Gradio sets table cells in the mono font; the landing page keeps mono for receipts only. */
.table-wrap th, .table-wrap .body-cell, .table-wrap .body-cell * {{
  font-family: var(--font) !important;
}}
.table-wrap th {{ color: {TEXT_SECONDARY}; font-weight: 500 !important; }}
/* The battlecard (render.py): a score header, then one card per claim, as in the landing
   page's receipt preview. */
.block.card:has(.bc) {{
  background: {SURFACE}; border: 1px solid {BORDER} !important; border-radius: 12px;
  padding: 28px !important;
}}
{PROGRESS_CSS}
{BATTLECARD_CSS}
footer {{ filter: grayscale(1); opacity: 0.6; }}
"""


def _logo_data_uri() -> str:
    raw = files("receipts.ui").joinpath("assets", "logo.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


LOGO_DATA_URI = _logo_data_uri()

HEADER_HTML = (
    '<header class="receipts-header">'
    '<div class="receipts-brand">'
    f'<img src="{LOGO_DATA_URI}" alt="{LOGO_ALT}" '
    f'width="{LOGO_WIDTH_PX}" height="{LOGO_HEIGHT_PX}">'
    f'<p class="receipts-tagline">{TAGLINE}</p>'
    "</div>"
    f'<a class="receipts-about" href="{LANDING_URL}" target="_blank" '
    'rel="noopener noreferrer">About</a>'
    "</header>"
)
