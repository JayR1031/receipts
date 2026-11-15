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
#progress textarea {{
  font-family: var(--font-mono); font-size: 0.8125rem; line-height: 1.6; color: {TEXT_SECONDARY};
}}
/* Gradio sets table cells in the mono font; the landing page keeps mono for receipts only. */
.table-wrap th, .table-wrap .body-cell, .table-wrap .body-cell * {{
  font-family: var(--font) !important;
}}
.table-wrap th {{ color: {TEXT_SECONDARY}; font-weight: 500 !important; }}
/* A rendered battlecard sits in a panel like the landing page's receipt preview. */
.block.card:has(h1) {{
  background: {SURFACE}; border: 1px solid {BORDER} !important; border-radius: {RADIUS};
  padding: 24px !important;
}}
.card a {{ color: {TEXT}; text-decoration: underline; text-underline-offset: 3px; }}
.card a:hover {{ color: {TEXT_SECONDARY}; }}
/* The only colours, for status marks; render.py wraps battlecard status marks in these classes. */
.status-verified {{ color: {VERIFIED}; }}
.status-dropped {{ color: {DROPPED}; }}
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
