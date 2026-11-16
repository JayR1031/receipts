"""The one seam through which identity reaches the UI (issue #41, ADR-0008).

Convention the `ui` and `wiring` tasks share: `create_app()` builds the live `Gate` and stores it
on `app.state.gate` before it calls `mount_ui(app)`, as it stores `run_starter` today.
`mount_ui` reads `getattr(app.state, "gate", None)`; with no `Gate` there, the UI behaves as it
did before issue #41.

UI handlers that need identity take Gradio's `gr.Request` and pass its Starlette request
(`gr.Request.request`) to `identify`. Gradio's mount-time auth hook (the dependency argument of
`mount_gradio_app`) is not used: it answers 401 to every signed-out visitor, and sign-in is
optional (option b).
"""

from __future__ import annotations

from typing import Protocol

from starlette.requests import Request

from receipts.auth.models import AccountStatus, SessionUser
from receipts.contracts import RunId, RunRequest, RunSummary


class Gate(Protocol):
    def identify(self, request: Request) -> SessionUser | None:
        """The user in a valid session cookie; `None` when signed out, tampered or expired."""
        ...

    async def start(self, request: RunRequest, passcode: str, user: SessionUser | None) -> RunId:
        """Start a run if the start rule allows it.

        Signed in: no passcode, counted against that user's daily limit. Signed out: the
        passcode must match, counted against the signed-out daily cap. A refusal raises
        `PermissionError` whose message is the `StartDecision.reason`; a missing key raises
        `MissingSettingError`, as today's `make_starter` does. No run starts either way.
        """
        ...

    async def history(self, user: SessionUser | None) -> list[RunSummary]:
        """That user's runs when signed in; the runs that belong to no user when signed out."""
        ...

    async def account(self, user: SessionUser | None) -> AccountStatus:
        """What the account line shows for this visitor today (UTC)."""
        ...
