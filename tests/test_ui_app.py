"""The Gradio UI's streaming generator, mount and secret hygiene (lane L5). No network."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import gradio as gr
from fastapi import FastAPI
from fastapi.testclient import TestClient

from receipts.contracts import RunEvent, RunId, RunRequest
from receipts.fakes import FakeRunService
from receipts.ui.app import UI_PATH, build_ui, mount_ui, resolve_service, run_stream
from receipts.ui.render import render_event_line

UI_DIR = Path(__file__).resolve().parents[1] / "src" / "receipts" / "ui"


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
    assert "**2 of 3 verified**" in card
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
    assert "verified**" in snapshots[-1][1]


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


def test_ui_module_reads_no_environment_and_no_settings() -> None:
    files = sorted(UI_DIR.glob("*.py"))
    assert files, f"no UI sources under {UI_DIR}"
    forbidden = re.compile(r"os\.environ|getenv|get_settings|receipts\.settings")
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
