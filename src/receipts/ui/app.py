# pyright: basic
"""The Gradio UI. W0 ships a stub so the mount is in place; L5 owns the real thing.

Gradio's public API is loosely typed, so this folder runs pyright in basic mode (ADR-0006);
that is also why `mount_ui` lives here and not in `receipts.api.app`.
"""

from __future__ import annotations

import gradio as gr
from fastapi import FastAPI

UI_PATH = "/ui"


def build_ui() -> gr.Blocks:
    """Return the Blocks app. No analytics: the container must make no outbound call."""
    with gr.Blocks(title="Receipts", analytics_enabled=False) as blocks:
        gr.Markdown("# Receipts\n\nEvery claim carries a receipt. The UI arrives with lane L5.")
    return blocks


def mount_ui(app: FastAPI) -> None:
    """Mount the UI at `/ui`. `ssr_mode=False`: no Node in the image."""
    gr.mount_gradio_app(app, build_ui(), path=UI_PATH, ssr_mode=False)
