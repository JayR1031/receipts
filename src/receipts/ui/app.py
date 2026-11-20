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

Sign-in (issue #41, ADR-0008): identity reaches the UI only through a `Gate` on
`app.state.gate`. With one, the header gains an account line (runs used today, a sign-in link or
a sign-out form), the passcode field shows only to signed-out visitors, runs start through
`gate.start` and History lists `gate.history` (own runs plus shared passcode / Ask Receipts
runs when signed in). Each handler that needs identity takes Gradio's `gr.Request` and hands
its Starlette request to `gate.identify`; Gradio's own auth hooks are not
used, because they turn every signed-out visitor away and sign-in is optional. With no `Gate`,
the UI behaves as it did before issue #41.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from html import escape
from typing import Any

import gradio as gr
from fastapi import FastAPI
from gradio.events import Dependency

from receipts.auth.gate import Gate
from receipts.auth.models import AccountStatus, SessionUser
from receipts.contracts import DoneEvent, RunEvent, RunId, RunRequest, RunService, RunSummary
from receipts.ui.demo import demo_service
from receipts.ui.render import (
    HISTORY_HEADERS,
    NO_CARD_HTML,
    render_battlecard,
    render_event_line,
    render_history,
    render_progress,
    render_progress_notice,
)
from receipts.ui.theme import CSS, HEADER_HTML, THEME

UI_PATH = "/ui"
SIGN_IN_PATH = "/auth/login"
SIGN_OUT_PATH = "/auth/logout"

# `(request, passcode) -> run_id`. W2 decides whether this goes in-process or over HTTP.
Starter = Callable[[RunRequest, str], Awaitable[RunId]]
Snapshot = tuple[str, str, str]  # (event log, battlecard HTML, progress view HTML)

PROGRESS_VIEW_ID = "run-view"  # theme.py styles the view by this id
NO_CARD = NO_CARD_HTML
BLANK_INPUT = "Enter a subject and rival to start."

START_LABEL = "Start run"
RUNNING_LABEL = "Running…"
FORM_HEAD = (
    "New comparison\n\n"
    "## Who can back up their claims?\n\n"
    "Name two companies. Receipts reads public pages about both and keeps only the claims "
    "it can quote back to a source."
)
FORM_HINT = "A run takes about 2 minutes."
HISTORY_NOTE = (
    "Your runs (when signed in) and shared runs started with the passcode or Ask Receipts. "
    "Other signed-in people's runs stay private. "
    "A voice run's Event log is on that run — it does not stream into another browser tab."
)


def _request(subject: str, rival: str, category: str | None) -> RunRequest:
    cat = (category or "").strip() or None
    return RunRequest(subject=subject.strip(), rival=rival.strip(), category=cat)


def _blank(subject: str, rival: str) -> bool:
    return not subject.strip() or not rival.strip()


def _notice(message: str) -> Snapshot:
    return (message, "", render_progress_notice(message))


async def _follow(service: RunService, run_id: RunId) -> AsyncIterator[Snapshot]:
    """One snapshot per event, then the card once the run is done."""
    events: list[RunEvent] = []
    lines: list[str] = []
    async for event in service.events(run_id):
        events.append(event)
        lines.append(render_event_line(event))
        yield ("\n".join(lines), "", render_progress(events))
        if isinstance(event, DoneEvent):
            break
    card = await service.get(run_id)
    card_html = render_battlecard(card, share=True) if card else NO_CARD
    yield ("\n".join(lines), card_html, render_progress(events))


async def run_stream(
    service: RunService,
    subject: str,
    rival: str,
    category: str | None,
    passcode: str,
    *,
    starter: Starter | None = None,
) -> AsyncIterator[Snapshot]:
    """Yield `(event_log, battlecard_html, progress_html)` snapshots: one per event, then the card
    once done."""
    if _blank(subject, rival):
        yield _notice(BLANK_INPUT)
        return
    request = _request(subject, rival, category)
    run_id = await (starter(request, passcode) if starter else service.start(request))
    async for snapshot in _follow(service, run_id):
        yield snapshot


def identify(gate: Gate, request: gr.Request | None) -> SessionUser | None:
    """The visitor's session user. Signed out when Gradio hands over no Starlette request."""
    starlette_request = request.request if request is not None else None
    return gate.identify(starlette_request) if starlette_request is not None else None


def _is_missing_setting(exc: BaseException) -> bool:
    # `MissingSettingError` names an unset variable, never its value. It lives in the settings
    # module, which no UI file may import (test_ui_module_reads_no_environment_and_no_settings),
    # so it is recognised by class name and every other RuntimeError still propagates.
    return any(cls.__name__ == "MissingSettingError" for cls in type(exc).__mro__)


def refusal_message(exc: BaseException) -> str | None:
    """What the visitor reads when `Gate.start` refuses (`PermissionError`, whose message is the
    start rule's reason with its count and denominator, or a missing setting); `None` otherwise."""
    if isinstance(exc, PermissionError) or _is_missing_setting(exc):
        return str(exc)
    return None


async def gated_run_stream(
    service: RunService,
    gate: Gate,
    request: gr.Request | None,
    subject: str,
    rival: str,
    category: str | None,
    passcode: str,
) -> AsyncIterator[Snapshot]:
    """`run_stream` when a `Gate` is wired: `gate.start` applies the start rule for this visitor,
    and a refusal is one notice in the progress view, never a traceback."""
    if _blank(subject, rival):
        yield _notice(BLANK_INPUT)
        return
    run_request = _request(subject, rival, category)
    try:
        run_id = await gate.start(run_request, passcode, identify(gate, request))
    except Exception as exc:
        message = refusal_message(exc)
        if message is None:
            raise
        yield _notice(message)
        return
    async for snapshot in _follow(service, run_id):
        yield snapshot


def render_account(status: AccountStatus) -> str:
    """The account line: today's count with its denominator and window, plus the one action."""
    count = f"{status.runs_used} of {status.runs_limit}"
    if status.email is not None:
        text = f"{escape(status.email)} · {count} runs used today (UTC)"
        action = (
            f'<form method="post" action="{SIGN_OUT_PATH}">'
            '<button type="submit" class="receipts-about">Sign out</button></form>'
        )
    else:
        text = f"{count} signed-out runs used today (UTC)"
        action = (
            f'<a class="receipts-about" href="{SIGN_IN_PATH}">Sign in with Google</a>'
            if status.sign_in_available
            else ""
        )
    return (
        '<div class="receipts-account">'
        f'<span class="receipts-account-text">{text}</span>{action}</div>'
    )


async def account_view(gate: Gate, request: gr.Request | None) -> tuple[str, dict[str, Any]]:
    """The account line and the passcode field's visibility, from one `gate.account` call:
    signed-in visitors start runs without a passcode, so the field is hidden for them."""
    status = await gate.account(identify(gate, request))
    return render_account(status), gr.update(visible=status.email is None)


async def history_view(
    service: RunService, gate: Gate | None, request: gr.Request | None
) -> tuple[list[list[str]], list[str]]:
    """History rows and their run ids through the `Gate` when one is wired (own runs plus
    shared passcode / Ask Receipts runs when signed in), otherwise `service.list()`."""
    rows: list[RunSummary] = await (
        service.list() if gate is None else gate.history(identify(gate, request))
    )
    return render_history(rows), [str(row.run_id) for row in rows]


def _plain_start(service: RunService, starter: Starter | None) -> Callable:
    async def on_start(
        subject: str, rival: str, category: str, passcode: str
    ) -> AsyncIterator[Snapshot]:
        async for snapshot in run_stream(
            service, subject, rival, category, passcode, starter=starter
        ):
            yield snapshot

    return on_start


def _gated_start(service: RunService, gate: Gate) -> Callable:
    async def on_start(
        subject: str, rival: str, category: str, passcode: str, request: gr.Request | None
    ) -> AsyncIterator[Snapshot]:
        async for snapshot in gated_run_stream(
            service, gate, request, subject, rival, category, passcode
        ):
            yield snapshot

    return on_start


def _start_handler(service: RunService, starter: Starter | None, gate: Gate | None) -> Callable:
    """The Start button's handler; both are named `on_start`, so its API name is the same."""
    return _plain_start(service, starter) if gate is None else _gated_start(service, gate)


def _busy() -> dict[str, Any]:
    return gr.update(value=RUNNING_LABEL, interactive=False)


def _ready() -> dict[str, Any]:
    return gr.update(value=START_LABEL, interactive=True)


def _run_form() -> tuple[gr.Textbox, gr.Textbox, gr.Textbox, gr.Textbox, gr.Button]:
    """The inputs and the Start button, laid out as one card (theme.py `FORM_CSS`)."""
    with gr.Column(elem_classes=["rf"]):
        gr.Markdown(FORM_HEAD, elem_classes=["rf-head"])
        with gr.Row(elem_classes=["rf-pair"]):
            subject = gr.Textbox(label="Subject", placeholder="Your company")
            gr.Markdown("vs", elem_classes=["rf-vs"])
            rival = gr.Textbox(label="Rival", placeholder="Their company")
        with gr.Row(elem_classes=["rf-extra"]):
            category = gr.Textbox(label="Category (optional)", placeholder="e.g. widgets")
            passcode = gr.Textbox(label="Passcode", type="password")
        with gr.Row(elem_classes=["rf-foot"]):
            gr.Markdown(FORM_HINT, elem_classes=["rf-hint"])
            start = gr.Button(START_LABEL, variant="primary", elem_id="start", scale=0)
    return subject, rival, category, passcode, start


def _run_panel(
    service: RunService, starter: Starter | None, gate: Gate | None
) -> tuple[gr.Textbox, gr.Button, Dependency]:
    subject, rival, category, passcode, start = _run_form()
    view = gr.HTML(elem_id=PROGRESS_VIEW_ID)
    with gr.Accordion("Event log", open=False, elem_classes=["rp-log"]):
        progress = gr.Textbox(label="Events", lines=12, interactive=False, elem_id="progress")
    card = gr.HTML(elem_classes=["card"])
    busy = start.click(_busy, outputs=[start], queue=False, api_visibility="private")
    started = busy.then(
        _start_handler(service, starter, gate),
        inputs=[subject, rival, category, passcode],
        outputs=[progress, card, view],
    )
    return passcode, start, started


def _history_panel(service: RunService, blocks: gr.Blocks, gate: Gate | None) -> None:
    gr.Markdown(HISTORY_NOTE)
    refresh = gr.Button("Refresh", size="sm", elem_id="refresh")
    table = gr.Dataframe(
        headers=list(HISTORY_HEADERS), type="array", interactive=False, label="Runs, newest first"
    )
    run_ids = gr.State([])
    card = gr.HTML(elem_classes=["card"])

    async def load(request: gr.Request | None) -> tuple[list[list[str]], list[str]]:
        return await history_view(service, gate, request)

    async def show(evt: gr.SelectData, ids: list[str]) -> str:
        row = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index
        if row is None or row >= len(ids):
            return ""
        found = await service.get(RunId(ids[row]))
        return render_battlecard(found, share=True) if found else NO_CARD

    refresh.click(load, outputs=[table, run_ids])
    blocks.load(load, outputs=[table, run_ids])
    table.select(show, inputs=[run_ids], outputs=[card])


def _wire_account(
    blocks: gr.Blocks, gate: Gate, account: gr.HTML, passcode: gr.Textbox, started: Dependency
) -> Dependency:
    """Fill the account line and the passcode field on page load, and recount after each run
    (a stale count would misstate how many runs are left today)."""

    async def on_account(request: gr.Request | None) -> tuple[str, dict[str, Any]]:
        return await account_view(gate, request)

    blocks.load(on_account, outputs=[account, passcode], api_name="account")
    return started.then(on_account, outputs=[account, passcode])


def build_ui(
    service: RunService, starter: Starter | None = None, *, gate: Gate | None = None
) -> gr.Blocks:
    """Return the Blocks app. No analytics: the container must make no outbound call.

    With a `gate`, runs start through `gate.start` and `starter` is unused."""
    with gr.Blocks(title="Receipts", analytics_enabled=False) as blocks:
        gr.HTML(HEADER_HTML)
        account = gr.HTML("", elem_id="account") if gate is not None else None
        with gr.Tab("Run"):
            passcode, start, started = _run_panel(service, starter, gate)
        with gr.Tab("History"):
            _history_panel(service, blocks, gate)
        last = started
        if gate is not None and account is not None:
            last = _wire_account(blocks, gate, account, passcode, started)
        # `.then` runs whether the run succeeded or raised, so the button never stays locked.
        last.then(_ready, outputs=[start], queue=False, api_visibility="private")
    return blocks


def resolve_service(app: FastAPI) -> RunService:
    """`app.state.run_service` when W2 set one; otherwise the demo replay."""
    service = getattr(app.state, "run_service", None)
    return service if service is not None else demo_service()


def _blocks_for(app: FastAPI) -> gr.Blocks:
    service = resolve_service(app)
    starter = getattr(app.state, "run_starter", None)  # W2's passcode-enforcing starter
    gate = getattr(app.state, "gate", None)  # issue #41: set by create_app() before mount_ui
    if gate is None:
        # Exactly the call made before issue #41 (tests/test_wiring.py spies on this signature).
        return build_ui(service, starter=starter)
    return build_ui(service, starter=starter, gate=gate)


def mount_ui(app: FastAPI) -> None:
    """Mount the UI at `/ui`. `ssr_mode=False`: no Node in the image.

    The `Gate`, when `create_app()` stored one on `app.state.gate`, is handed to `build_ui`; it is
    never given to Gradio as an auth hook, so `/ui` stays open to signed-out visitors."""
    gr.mount_gradio_app(app, _blocks_for(app), path=UI_PATH, ssr_mode=False, theme=THEME, css=CSS)
