# pyright: basic
"""The Gradio UI, mounted at `/ui` (lane L5).

Gradio's public API is loosely typed, so this folder runs pyright in basic mode (ADR-0006);
that is also why `mount_ui` lives here and not in `receipts.api.app`.

Wiring: `mount_ui(app)` takes the `RunService` from `app.state.run_service` when W2 has set
one, and otherwise replays the demo script (`receipts.ui.demo`). `build_ui(service)` is the
seam both paths share.

Passcode: the Run panel only passes the typed passcode along. The UI never validates it and
never reads a secret or an environment variable; the server side (L4's `POST /api/runs`, W2)
enforces it. The default `starter` calls `service.start(request)` in-process and ignores the
passcode; W2 may inject a `starter` that posts to the API with it instead.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable

import gradio as gr
from fastapi import FastAPI

from receipts.contracts import DoneEvent, RunId, RunRequest, RunService
from receipts.ui.demo import demo_service
from receipts.ui.render import (
    HISTORY_HEADERS,
    render_battlecard,
    render_event_line,
    render_history,
)
from receipts.ui.theme import CSS, HEADER_HTML, THEME

UI_PATH = "/ui"

# `(request, passcode) -> run_id`. W2 decides whether this goes in-process or over HTTP.
Starter = Callable[[RunRequest, str], Awaitable[RunId]]

NO_CARD = "_Run finished but no battlecard was stored._"


def _request(subject: str, rival: str, category: str | None) -> RunRequest:
    cat = (category or "").strip() or None
    return RunRequest(subject=subject.strip(), rival=rival.strip(), category=cat)


async def run_stream(
    service: RunService,
    subject: str,
    rival: str,
    category: str | None,
    passcode: str,
    *,
    starter: Starter | None = None,
) -> AsyncIterator[tuple[str, str]]:
    """Yield `(progress_log, battlecard_md)` snapshots: one per event, then the card once done."""
    if not subject.strip() or not rival.strip():
        yield ("Enter a subject and rival to start.", "")
        return
    request = _request(subject, rival, category)
    run_id = await (starter(request, passcode) if starter else service.start(request))
    lines: list[str] = []
    async for event in service.events(run_id):
        lines.append(render_event_line(event))
        yield ("\n".join(lines), "")
        if isinstance(event, DoneEvent):
            break
    card = await service.get(run_id)
    yield ("\n".join(lines), render_battlecard(card) if card else NO_CARD)


def _run_panel(service: RunService, starter: Starter | None) -> None:
    with gr.Row():
        subject = gr.Textbox(label="Subject", placeholder="Your company")
        rival = gr.Textbox(label="Rival", placeholder="Their company")
    with gr.Row():
        category = gr.Textbox(label="Category (optional)", placeholder="e.g. widgets")
        passcode = gr.Textbox(label="Passcode", type="password")
    start = gr.Button("Start run", variant="primary")
    progress = gr.Textbox(label="Progress", lines=12, interactive=False, elem_id="progress")
    card = gr.Markdown(elem_classes=["card"])

    async def on_start(
        subject: str, rival: str, category: str, passcode: str
    ) -> AsyncIterator[tuple[str, str]]:
        async for snapshot in run_stream(
            service, subject, rival, category, passcode, starter=starter
        ):
            yield snapshot

    start.click(on_start, inputs=[subject, rival, category, passcode], outputs=[progress, card])


def _history_panel(service: RunService, blocks: gr.Blocks) -> None:
    refresh = gr.Button("Refresh")
    table = gr.Dataframe(
        headers=list(HISTORY_HEADERS), type="array", interactive=False, label="Runs, newest first"
    )
    run_ids = gr.State([])
    card = gr.Markdown(elem_classes=["card"])

    async def load() -> tuple[list[list[str]], list[str]]:
        rows = await service.list()
        return render_history(rows), [str(row.run_id) for row in rows]

    async def show(evt: gr.SelectData, ids: list[str]) -> str:
        row = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index
        if row is None or row >= len(ids):
            return ""
        found = await service.get(RunId(ids[row]))
        return render_battlecard(found) if found else NO_CARD

    refresh.click(load, outputs=[table, run_ids])
    blocks.load(load, outputs=[table, run_ids])
    table.select(show, inputs=[run_ids], outputs=[card])


def build_ui(service: RunService, starter: Starter | None = None) -> gr.Blocks:
    """Return the Blocks app. No analytics: the container must make no outbound call."""
    with gr.Blocks(title="Receipts", analytics_enabled=False) as blocks:
        gr.HTML(HEADER_HTML)
        with gr.Tab("Run"):
            _run_panel(service, starter)
        with gr.Tab("History"):
            _history_panel(service, blocks)
    return blocks


def resolve_service(app: FastAPI) -> RunService:
    """`app.state.run_service` when W2 set one; otherwise the demo replay."""
    service = getattr(app.state, "run_service", None)
    return service if service is not None else demo_service()


def mount_ui(app: FastAPI) -> None:
    """Mount the UI at `/ui`. `ssr_mode=False`: no Node in the image."""
    service = resolve_service(app)
    gr.mount_gradio_app(app, build_ui(service), path=UI_PATH, ssr_mode=False, theme=THEME, css=CSS)
