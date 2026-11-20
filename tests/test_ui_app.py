"""The Gradio UI's streaming generator, mount, the `Gate` seam and secret hygiene (lane L5).

No network. The `Gate` tests use `FakeGate` below; identities are synthetic (`example.com`).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import gradio as gr
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

import receipts.ui.app as ui_app
from receipts.auth.models import AccountStatus, SessionUser
from receipts.contracts import RunEvent, RunId, RunRequest, RunSummary
from receipts.fakes import FakeRunService, data
from receipts.settings import MissingSettingError
from receipts.ui.app import UI_PATH, build_ui, mount_ui, resolve_service, run_stream
from receipts.ui.render import render_event_line, render_history
from receipts.ui.theme import HEADER_HTML

UI_DIR = Path(__file__).resolve().parents[1] / "src" / "receipts" / "ui"

USER = SessionUser(user_id="user-0001", expires_at=datetime(2026, 11, 22, tzinfo=UTC))
EMAIL = "visitor-0001@example.com"
SIGNED_IN = AccountStatus(email=EMAIL, runs_used=0, runs_limit=5, sign_in_available=True)
SIGNED_OUT = AccountStatus(email=None, runs_used=3, runs_limit=20, sign_in_available=True)
NO_SIGN_IN = AccountStatus(email=None, runs_used=0, runs_limit=20, sign_in_available=False)
LIMIT_REASON = "5 of 5 runs used today (UTC); the limit resets at 00:00 UTC"
COOKIE = ("receipts_session", "fake-session-token")


class FakeGate:
    """A `Gate` that records every call; `identify` returns the configured user."""

    def __init__(
        self,
        service: FakeRunService,
        *,
        user: SessionUser | None,
        status: AccountStatus,
        history: list[RunSummary] | None = None,
        refusal: Exception | None = None,
    ) -> None:
        self.service = service
        self.user = user
        self.status = status
        self.rows = history or []
        self.refusal = refusal
        self.identified: list[Request] = []
        self.started: list[tuple[RunRequest, str, SessionUser | None]] = []
        self.history_for: list[SessionUser | None] = []
        self.account_for: list[SessionUser | None] = []

    def identify(self, request: Request) -> SessionUser | None:
        self.identified.append(request)
        return self.user

    async def start(self, request: RunRequest, passcode: str, user: SessionUser | None) -> RunId:
        self.started.append((request, passcode, user))
        if self.refusal is not None:
            raise self.refusal
        return await self.service.start(request)

    async def history(self, user: SessionUser | None) -> list[RunSummary]:
        self.history_for.append(user)
        return self.rows

    async def account(self, user: SessionUser | None) -> AccountStatus:
        self.account_for.append(user)
        return self.status


def _gr_request() -> gr.Request:
    """What Gradio hands a handler: a `gr.Request` around the Starlette request, cookie and all."""
    name, value = COOKIE
    scope = {
        "type": "http",
        "method": "POST",
        "path": f"{UI_PATH}/gradio_api/queue/join",
        "headers": [(b"cookie", f"{name}={value}".encode())],
        "query_string": b"",
    }
    return gr.Request(request=Request(scope))


def _summary(run_id: str) -> RunSummary:
    return RunSummary(
        run_id=RunId(run_id),
        subject="Acme Widgets",
        rival="Zeta Gadgets",
        status="done",
        verified_count=2,
        total_count=3,
        started_at=data.T0,
    )


def _mounted(gate: FakeGate) -> TestClient:
    app = FastAPI()
    app.state.gate = gate
    mount_ui(app)
    client = TestClient(app)
    client.cookies.set(*COOKIE)
    return client


def _call(client: TestClient, api_name: str, inputs: list[Any]) -> list[Any]:
    """Gradio's direct (non-queue) API: one call, the handler's first output."""
    response = client.post(
        f"{UI_PATH}/gradio_api/run/{api_name}", json={"data": inputs, "session_hash": "test"}
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def test_run_stream_yields_lines_in_event_order_then_the_battlecard(
    fake_run_service: FakeRunService, sample_events: list[RunEvent]
) -> None:
    snapshots = [
        snap
        async for snap in run_stream(
            fake_run_service, "Acme Widgets", "Zeta Gadgets", "widgets", "secret-pass"
        )
    ]
    assert snapshots, "the generator yielded nothing"
    progress_log, card = snapshots[-1]
    lines = [line for line in progress_log.splitlines() if line.strip()]
    expected = [render_event_line(event) for event in sample_events]
    assert lines[-len(expected) :] == expected, "lines are not in event order"
    assert 'aria-label="2 of 3 claims verified"' in card
    assert "Acme Widgets" in card and "Zeta Gadgets" in card
    # the card appears only once the run is done, never before
    assert all(c == "" for _, c in snapshots[:-1])
    # the request went to the service; the passcode is passed along, never validated here
    assert fake_run_service.requests[fake_run_service.run_id] == RunRequest(
        subject="Acme Widgets", rival="Zeta Gadgets", category="widgets"
    )


async def test_run_stream_hands_the_passcode_to_the_injected_starter(
    fake_run_service: FakeRunService,
) -> None:
    seen: list[tuple[RunRequest, str]] = []

    async def starter(request: RunRequest, passcode: str) -> RunId:
        seen.append((request, passcode))
        return await fake_run_service.start(request)

    snapshots = [
        snap async for snap in run_stream(fake_run_service, "A", "B", "", "pw-123", starter=starter)
    ]
    assert seen == [(RunRequest(subject="A", rival="B", category=None), "pw-123")]
    assert "claims verified" in snapshots[-1][1]


async def test_run_stream_rejects_blank_subject_or_rival(fake_run_service: FakeRunService) -> None:
    snapshots = [snap async for snap in run_stream(fake_run_service, "  ", "B", None, "")]
    assert len(snapshots) == 1
    assert "subject and rival" in snapshots[0][0].lower()
    assert fake_run_service.requests == {}


def test_build_ui_takes_a_service_and_returns_blocks(fake_run_service: FakeRunService) -> None:
    blocks = build_ui(fake_run_service)
    assert isinstance(blocks, gr.Blocks)
    assert blocks.analytics_enabled is False


def test_mount_ui_on_a_bare_app_falls_back_to_the_demo_service() -> None:
    app = FastAPI()
    assert resolve_service(app) is not None
    mount_ui(app)
    assert TestClient(app).get(UI_PATH).status_code == 200


def test_resolve_service_prefers_app_state(fake_run_service: FakeRunService) -> None:
    app = FastAPI()
    app.state.run_service = fake_run_service
    assert resolve_service(app) is fake_run_service


def test_ui_path_is_stable() -> None:
    assert UI_PATH == "/ui"


def test_mount_ui_serves_config_with_css_and_theme_stylesheet() -> None:
    app = FastAPI()
    mount_ui(app)
    client = TestClient(app)

    config = client.get(f"{UI_PATH}/config")
    assert config.status_code == 200
    payload = config.json()
    assert ".status-verified" in payload.get("css", "")

    theme_css = client.get(f"{UI_PATH}/theme.css")
    assert theme_css.status_code == 200
    assert "#000000" in theme_css.text


def test_ui_module_reads_no_environment_and_no_settings() -> None:
    files = sorted(UI_DIR.glob("*.py"))
    assert files, f"no UI sources under {UI_DIR}"
    # `auth_dependency`: Gradio answers 401 to every signed-out visitor with it (brief, issue #41)
    forbidden = re.compile(r"os\.environ|getenv|get_settings|receipts\.settings|auth_dependency")
    offenders = [
        f"{path.name}:{n}: {line.strip()}"
        for path in files
        for n, line in enumerate(path.read_text().splitlines(), start=1)
        if forbidden.search(line)
    ]
    assert offenders == []
    for path in files:
        assert path.read_text().startswith("# pyright: basic"), (
            f"{path.name} lacks the ADR-0006 header"
        )


def test_ui_module_imports_with_an_empty_environment() -> None:
    proc = subprocess.run(
        [
            "env",
            "-i",
            f"PATH={os.environ.get('PATH', '')}",
            f"HOME={os.environ.get('HOME', '')}",
            sys.executable,
            "-c",
            "import receipts.ui.app",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


# --- the `Gate` seam (issue #41): identity reaches the UI only through `app.state.gate` ---


def test_identify_hands_the_gate_the_starlette_request(fake_run_service: FakeRunService) -> None:
    gate = FakeGate(fake_run_service, user=USER, status=SIGNED_IN)
    request = _gr_request()
    assert ui_app.identify(gate, request) == USER
    assert gate.identified == [request.request]
    assert gate.identified[0].cookies == dict([COOKIE])


def test_identify_with_no_starlette_request_is_signed_out(fake_run_service: FakeRunService) -> None:
    gate = FakeGate(fake_run_service, user=USER, status=SIGNED_IN)
    assert ui_app.identify(gate, None) is None
    assert ui_app.identify(gate, gr.Request()) is None
    assert gate.identified == [], "the gate was asked about a request that does not exist"


async def test_account_view_signed_in_shows_the_count_a_sign_out_form_and_hides_the_passcode(
    fake_run_service: FakeRunService,
) -> None:
    gate = FakeGate(fake_run_service, user=USER, status=SIGNED_IN)
    html, passcode = await ui_app.account_view(gate, _gr_request())
    assert f"{EMAIL} · 0 of 5 runs used today (UTC)" in html
    assert f'<form method="post" action="{ui_app.SIGN_OUT_PATH}">' in html
    assert ui_app.SIGN_OUT_PATH == "/auth/logout"
    assert "Sign out</button>" in html
    assert "Sign in with Google" not in html
    assert passcode == gr.update(visible=False)
    assert gate.account_for == [USER]


async def test_account_view_signed_out_offers_sign_in_and_shows_the_passcode(
    fake_run_service: FakeRunService,
) -> None:
    gate = FakeGate(fake_run_service, user=None, status=SIGNED_OUT)
    html, passcode = await ui_app.account_view(gate, _gr_request())
    assert "3 of 20 signed-out runs used today (UTC)" in html
    assert f'href="{ui_app.SIGN_IN_PATH}"' in html
    assert ui_app.SIGN_IN_PATH == "/auth/login"
    assert ">Sign in with Google</a>" in html
    assert ui_app.SIGN_OUT_PATH not in html
    assert passcode == gr.update(visible=True)
    assert gate.account_for == [None]


async def test_account_view_hides_sign_in_when_the_deploy_cannot_offer_it(
    fake_run_service: FakeRunService,
) -> None:
    gate = FakeGate(fake_run_service, user=None, status=NO_SIGN_IN)
    html, passcode = await ui_app.account_view(gate, _gr_request())
    assert "0 of 20 signed-out runs used today (UTC)" in html
    assert "Sign in with Google" not in html
    assert ui_app.SIGN_IN_PATH not in html
    assert passcode == gr.update(visible=True)


def test_render_account_escapes_the_email() -> None:
    status = SIGNED_IN.model_copy(update={"email": '<img src=x onerror="alert(1)">@example.com'})
    html = ui_app.render_account(status)
    assert "<img" not in html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;@example.com" in html


async def test_gated_run_stream_starts_through_the_gate_with_the_user_and_typed_passcode(
    fake_run_service: FakeRunService,
) -> None:
    gate = FakeGate(fake_run_service, user=USER, status=SIGNED_IN)
    snapshots = [
        snap
        async for snap in ui_app.gated_run_stream(
            fake_run_service, gate, _gr_request(), "Acme Widgets", "Zeta Gadgets", "widgets", "pw-1"
        )
    ]
    request = RunRequest(subject="Acme Widgets", rival="Zeta Gadgets", category="widgets")
    assert gate.started == [(request, "pw-1", USER)]
    assert 'aria-label="2 of 3 claims verified"' in snapshots[-1][1]
    assert all(card == "" for _, card in snapshots[:-1])


async def test_gated_run_stream_shows_a_refusal_with_its_count_in_the_progress_box(
    fake_run_service: FakeRunService,
) -> None:
    gate = FakeGate(
        fake_run_service, user=USER, status=SIGNED_IN, refusal=PermissionError(LIMIT_REASON)
    )
    snapshots = [
        snap
        async for snap in ui_app.gated_run_stream(
            fake_run_service, gate, _gr_request(), "A", "B", None, ""
        )
    ]
    assert snapshots == [(LIMIT_REASON, "")]
    assert fake_run_service.requests == {}, "a refused start must start no run"


async def test_gated_run_stream_names_a_missing_setting_and_never_its_value(
    fake_run_service: FakeRunService,
) -> None:
    gate = FakeGate(
        fake_run_service,
        user=None,
        status=SIGNED_OUT,
        refusal=MissingSettingError("KEENABLE_API_KEY"),
    )
    snapshots = [
        snap
        async for snap in ui_app.gated_run_stream(
            fake_run_service, gate, _gr_request(), "A", "B", None, "pw-1"
        )
    ]
    assert snapshots == [("KEENABLE_API_KEY is not set", "")]
    assert gate.started[0][2] is None
    assert fake_run_service.requests == {}


async def test_gated_run_stream_lets_an_unexpected_error_through(
    fake_run_service: FakeRunService,
) -> None:
    gate = FakeGate(fake_run_service, user=USER, status=SIGNED_IN, refusal=RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        async for _ in ui_app.gated_run_stream(
            fake_run_service, gate, _gr_request(), "A", "B", None, ""
        ):
            pass


async def test_gated_run_stream_rejects_blank_subject_or_rival_before_the_gate(
    fake_run_service: FakeRunService,
) -> None:
    gate = FakeGate(fake_run_service, user=USER, status=SIGNED_IN)
    snapshots = [
        snap
        async for snap in ui_app.gated_run_stream(
            fake_run_service, gate, _gr_request(), "A", "  ", None, ""
        )
    ]
    assert len(snapshots) == 1
    assert "subject and rival" in snapshots[0][0].lower()
    assert gate.started == []


async def test_history_view_lists_the_visitors_runs_from_the_gate(
    fake_run_service: FakeRunService,
) -> None:
    await fake_run_service.start(RunRequest(subject="Other", rival="Run"))  # service.list() only
    mine = _summary("run-user-0001")
    gate = FakeGate(fake_run_service, user=USER, status=SIGNED_IN, history=[mine])
    rows, ids = await ui_app.history_view(fake_run_service, gate, _gr_request())
    assert rows == render_history([mine])
    assert ids == ["run-user-0001"]
    assert gate.history_for == [USER]


async def test_history_view_without_a_gate_lists_the_service(
    fake_run_service: FakeRunService,
) -> None:
    await fake_run_service.start(RunRequest(subject="A", rival="B"))
    rows, ids = await ui_app.history_view(fake_run_service, None, None)
    assert rows == render_history(await fake_run_service.list())
    assert ids == [str(fake_run_service.run_id)]


def test_build_ui_with_a_gate_puts_the_account_line_right_after_the_header(
    fake_run_service: FakeRunService,
) -> None:
    gate = FakeGate(fake_run_service, user=None, status=SIGNED_OUT)
    blocks = build_ui(fake_run_service, gate=gate)
    htmls = sorted(
        (
            b
            for b in blocks.blocks.values()
            if isinstance(b, gr.HTML) and "card" not in (b.elem_classes or [])
        ),
        key=lambda b: b._id,
    )
    assert len(htmls) == 2
    assert htmls[0].value == HEADER_HTML
    assert htmls[0] is min(blocks.blocks.values(), key=lambda b: b._id)


def test_build_ui_with_a_gate_recounts_the_account_line_after_each_run(
    fake_run_service: FakeRunService,
) -> None:
    """A run moves today's count, so the line is refreshed once the run's stream ends."""
    gate = FakeGate(fake_run_service, user=USER, status=SIGNED_IN)
    deps = build_ui(fake_run_service, gate=gate).get_config_file().get("dependencies", [])
    by_name = {dep["api_name"]: dep for dep in deps}
    start, account = by_name["on_start"], by_name["account"]
    after_start = [dep for dep in deps if dep["trigger_after"] == start["id"]]
    assert [dep["outputs"] for dep in after_start] == [account["outputs"]]


def test_mount_ui_reads_the_gate_from_app_state_and_identifies_by_cookie(
    fake_run_service: FakeRunService,
) -> None:
    gate = FakeGate(fake_run_service, user=USER, status=SIGNED_IN)
    html, passcode = _call(_mounted(gate), "account", [])
    assert f"{EMAIL} · 0 of 5 runs used today (UTC)" in html
    assert passcode["visible"] is False
    assert len(gate.identified) == 1
    assert isinstance(gate.identified[0], Request)
    assert gate.identified[0].cookies == dict([COOKIE])
    assert gate.account_for == [USER]


def test_mount_ui_with_a_gate_starts_runs_through_it(fake_run_service: FakeRunService) -> None:
    gate = FakeGate(
        fake_run_service, user=USER, status=SIGNED_IN, refusal=PermissionError(LIMIT_REASON)
    )
    progress, card = _call(_mounted(gate), "on_start", ["A", "B", "", "pw-1"])
    assert (progress, card) == (LIMIT_REASON, "")
    assert gate.started == [(RunRequest(subject="A", rival="B"), "pw-1", USER)]


def test_mount_ui_with_a_gate_lists_history_through_it(fake_run_service: FakeRunService) -> None:
    gate = FakeGate(
        fake_run_service, user=USER, status=SIGNED_IN, history=[_summary("run-user-0001")]
    )
    table, _ids_state = _call(_mounted(gate), "load", [])  # Gradio never sends a gr.State out
    assert table["data"] == render_history([_summary("run-user-0001")])
    assert gate.history_for == [USER]


def test_mount_ui_with_a_gate_stays_open_to_signed_out_visitors(
    fake_run_service: FakeRunService,
) -> None:
    gate = FakeGate(fake_run_service, user=None, status=SIGNED_OUT)
    client = _mounted(gate)
    client.cookies.clear()
    assert client.get(UI_PATH).status_code == 200
    assert client.get(f"{UI_PATH}/config").status_code == 200
    html, passcode = _call(client, "account", [])
    assert "3 of 20 signed-out runs used today (UTC)" in html
    assert passcode["visible"] is True
