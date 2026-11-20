# pyright: basic
"""The public, read-only share page for one battlecard (lane L5; `receipts.api.share` serves it).

A whole HTML document, not a Gradio page: it loads fast, works without JavaScript, and carries
Open Graph and Twitter tags so a pasted link previews as "Subject vs Rival: N of M claims
verified". The preview image is the landing page's 1200x630 card (`assets/share-card.png`).

The page shows nothing `GET /api/runs/{run_id}` does not already return to anyone with the run
id. It asks search engines not to index it: runs quote public pages, and those can name people.
Every value from the run is escaped, as in `render.py`.
"""

from __future__ import annotations

from html import escape
from importlib.resources import files

from receipts.contracts import Battlecard
from receipts.ui.render import render_battlecard, share_path
from receipts.ui.theme import (
    BATTLECARD_CSS,
    BLACK,
    BORDER,
    BORDER_FOCUS,
    LANDING_URL,
    LOGO_ALT,
    LOGO_DATA_URI,
    LOGO_HEIGHT_PX,
    LOGO_WIDTH_PX,
    RADIUS,
    SURFACE,
    TAGLINE,
    TEXT,
    TEXT_SECONDARY,
)

SHARE_IMAGE_PATH = "/share/card.png"
SHARE_IMAGE_ALT = (
    "Receipts: every claim carries a receipt. AI agents compare two companies, and a plain-code "
    "verifier checks every quote."
)
APP_PATH = "/ui/"
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1"})

PAGE_CSS = f"""
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: {BLACK}; color: {TEXT};
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: ui-monospace, "SF Mono", Menlo, monospace;
}}
.share {{ max-width: 880px; margin: 0 auto; padding: 24px 20px 64px; }}
.share-top {{
  display: flex; align-items: center; gap: 16px; padding-bottom: 20px;
}}
.share-top img {{ height: {LOGO_HEIGHT_PX}px; width: auto; display: block; }}
.share-top p {{
  margin: 0; padding-left: 16px; border-left: 1px solid {BORDER}; color: {TEXT_SECONDARY};
  font-size: 0.875rem;
}}
.share-panel {{
  background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; padding: 28px;
}}
.share-cta {{
  display: flex; flex-wrap: wrap; align-items: center; gap: 12px 20px; margin-top: 24px;
  color: {TEXT_SECONDARY}; font-size: 0.875rem; line-height: 1.5;
}}
.share-cta p {{ flex: 1 1 320px; margin: 0; }}
.share-btn {{
  background: {TEXT}; color: {BLACK}; font-weight: 600; text-decoration: none;
  padding: 10px 18px; border-radius: {RADIUS};
}}
.share-link {{ color: {TEXT}; text-underline-offset: 3px; }}
.share-link:hover, .share-btn:hover {{ opacity: 0.85; }}
a:focus-visible {{ outline: 2px solid {BORDER_FOCUS}; outline-offset: 2px; }}
@media (max-width: 640px) {{
  .share-top {{ flex-direction: column; align-items: flex-start; gap: 6px; }}
  .share-top p {{ border-left: 0; padding-left: 0; }}
  .share-panel {{ padding: 20px 16px; }}
}}
"""


def share_image() -> bytes:
    return files("receipts.ui").joinpath("assets", "share-card.png").read_bytes()


def origin(host: str) -> str:
    """The page's own origin for absolute preview URLs: `http` on a local host, else `https`."""
    name = host.rsplit(":", 1)[0] if not host.startswith("[") else host
    scheme = "http" if name in LOCAL_HOSTS else "https"
    return f"{scheme}://{host}"


def share_title(card: Battlecard) -> str:
    return (
        f"{card.subject} vs {card.rival}: {card.verified_count} of {card.total_count} "
        "claims verified"
    )


def _description(card: Battlecard) -> str:
    return (
        f"A Receipts battlecard: AI agents compared {card.subject} and {card.rival} on the web, "
        "and plain code checked every claim against the page or search result it cites."
    )


def _head(title: str, description: str, page_url: str, image_url: str) -> str:
    t, d = escape(title, quote=True), escape(description, quote=True)
    page, image = escape(page_url, quote=True), escape(image_url, quote=True)
    alt = escape(SHARE_IMAGE_ALT, quote=True)
    return (
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{t} · Receipts</title>"
        f'<meta name="description" content="{d}">'
        '<meta name="robots" content="noindex">'
        f'<link rel="canonical" href="{page}">'
        '<meta property="og:type" content="website">'
        '<meta property="og:site_name" content="Receipts">'
        f'<meta property="og:title" content="{t}">'
        f'<meta property="og:description" content="{d}">'
        f'<meta property="og:url" content="{page}">'
        f'<meta property="og:image" content="{image}">'
        '<meta property="og:image:width" content="1200">'
        '<meta property="og:image:height" content="630">'
        f'<meta property="og:image:alt" content="{alt}">'
        '<meta name="twitter:card" content="summary_large_image">'
        f'<meta name="twitter:title" content="{t}">'
        f'<meta name="twitter:description" content="{d}">'
        f'<meta name="twitter:image" content="{image}">'
        f"<style>{PAGE_CSS}{BATTLECARD_CSS}</style>"
    )


def _page(head: str, body: str) -> str:
    top = (
        '<header class="share-top">'
        f'<a href="{APP_PATH}"><img src="{LOGO_DATA_URI}" alt="{LOGO_ALT}" '
        f'width="{LOGO_WIDTH_PX}" height="{LOGO_HEIGHT_PX}"></a>'
        f"<p>{TAGLINE}</p></header>"
    )
    cta = (
        '<footer class="share-cta">'
        "<p>Each claim links to the page or search result it came from. A claim whose receipt "
        "does not check out is folded under its section, with the reason.</p>"
        f'<a class="share-btn" href="{APP_PATH}">Run your own comparison</a>'
        f'<a class="share-link" href="{LANDING_URL}">How it works</a>'
        "</footer>"
    )
    return (
        f'<!doctype html><html lang="en"><head>{head}</head><body><main class="share">'
        f'{top}<section class="share-panel">{body}</section>{cta}</main></body></html>'
    )


def render_share_page(card: Battlecard, *, host: str) -> str:
    base = origin(host)
    head = _head(
        share_title(card), _description(card), base + share_path(card), base + SHARE_IMAGE_PATH
    )
    return _page(head, render_battlecard(card))


def render_missing_page(*, host: str) -> str:
    base = origin(host)
    title = "Battlecard not found"
    description = "This battlecard does not exist, or its run has not finished yet."
    head = _head(title, description, base + APP_PATH, base + SHARE_IMAGE_PATH)
    body = f'<div class="bc"><p class="bc-empty">{description}</p></div>'
    return _page(head, body)
