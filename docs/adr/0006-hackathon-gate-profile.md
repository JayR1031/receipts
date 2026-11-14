# ADR-0006: Hackathon gate profile

**Status:** accepted · **Date:** 2026-11-14 · Wave 0, issue #12. Expires with the hackathon: every exception here has a date.

## Context

AGENTS.md section 9 allows exactly two gate relaxations, and only the ones this ADR records: pyright basic mode for `src/receipts/ui/` and pip-audit ignores for advisories in the Gradio or LangChain dependency tree, each with an expiry no later than 2026-11-30. Everything else (format, lint, tests, gitleaks `--exit-code 1`, leak gate, `pip-audit --strict`) is fully enforced. This ADR also records the Wave 0 tooling choices the W1 lanes depend on but may not change (`pyproject.toml` and `uv.lock` are frozen after W0).

## Decision

### Pyright

`[tool.pyright]` keeps `include = ["src", "tests"]` and sets `strict = ["src"]`, so every module under `src/receipts/` (including `src/receipts/__init__.py` and any top-level module a later wave adds) is checked in strict mode without a list to maintain. `src/receipts/ui/` opts down per file: every `.py` there, `__init__.py` included, starts with `# pyright: basic`, which overrides the strict path for that file. The reason is that Gradio's public API is partially typed (`gr.mount_gradio_app` reports `reportUnknownMemberType` under strict); for that reason the mount call lives in `src/receipts/ui/app.py` (`mount_ui(app)`), and `src/receipts/api/app.py` stays strict and calls it. Proof recorded at repair time: `def f(x): return x` appended to `src/receipts/ui/app.py` gives 0 errors; the same line in `src/receipts/__init__.py` gives 4 errors. No `# type: ignore`, no global `typeCheckingMode` change, `tests` stays included.

### pip-audit

**0 advisories ignored, audited at `b145d02`** (the commit that locked `uv.lock`, unchanged since): `uv run pip-audit --strict --vulnerability-service osv` printed `No known vulnerabilities found` over the 118 locked packages. `.github/workflows/security.yml:37` is untouched. If an advisory appears before 2026-11-30 it is added to the table below and as one `--ignore-vuln <ID>` flag on that line, nowhere else.

| Advisory | Package | Why it does not apply here | Expires |
|---|---|---|---|
| (none) | | | |

### Async test plugin

`pytest-asyncio` (1.5.0 locked) with `asyncio_mode = "auto"` and `asyncio_default_fixture_loop_scope = "function"` in `pyproject.toml`. Lanes write `async def test_...` with no marker. Chosen over anyio's plugin (present through httpx) because anyio needs an `anyio_backend` fixture and markers on every test, and nothing here uses trio.

### `effort` pass-through in `langchain-anthropic`

Read from the installed package, no API call: `langchain-anthropic` 1.7.10, `langchain_anthropic/chat_models.py` lines 1526–1541 declare `reasoning_effort: Literal["max", "xhigh", "high", "medium", "low"] | None = Field(alias="effort")`, which "Configures `output_config.effort`", and the docstring says `effort` "is also accepted as an alias for this field, at both construction and call time". **Confirmed:** L1 passes `DomainPack.effort` straight through as `ChatAnthropic(model=pack.model, effort=pack.effort)`; `contracts.Effort` is the same five-value literal. No fallback parameter is needed.

### Contract decisions lanes rely on

`RunRepo` and `RunService` methods are `async` (`contracts.py:209-228`); `SearchClient.search` and `FetchClient.fetch` are sync (`:201-206`). `DomainPack.id` is typed `Domain`, and beyond the brief's `max_searches=3`/`max_fetches=4` the defaults are `effort=None`, `source_allow=()`, `source_deny=()`, `timeout_s=120`, `extra_fields=()`, `rubric=""`; `Claim.verified` defaults to `False`. Consequences: L4 needs `create_async_engine(sqlalchemy_url(...), pool_pre_ping=True)` because `RunRepo` is async (aiosqlite and psycopg are locked). L5 must keep `mount_ui(app: FastAPI) -> None` and `UI_PATH` in `src/receipts/ui/app.py` stable, because `src/receipts/api/app.py` (L4's file, W0 lines) imports and calls both; wiring a `RunService` into the UI is W2's job.

### W1 lane rules (scope cut 2026-11-14: 2 packs, one `runs` table, no Haiku note)

Each lane touches only its globs; tests live in `tests/` (the only folder pytest collects); unit tests use `receipts.fakes` and make no network call; `bin/jig` green then `/judge` before merge.

| Lane | Issue | Allowed globs |
|---|---|---|
| L1 harness | #13 | `src/receipts/harness/**`, `tests/test_harness*.py` |
| L2 verifier | #14 | `src/receipts/verify/**`, `tests/test_verify*.py` |
| L3 packs (`pricing`, `positioning_seo`) + 1 golden fixture | #15 | `src/receipts/packs/**`, `tests/fixtures/**`, `tests/test_packs*.py` |
| L4 one `runs` table + `/api/runs*` | #16 | `src/receipts/db/**`, `src/receipts/api/**` (not the W0 `mount_ui`/redirect lines), `tests/test_db*.py`, `tests/test_api*.py`, `tests/test_openapi_export.py`, `scripts/export_openapi.py`, `docs/api/openapi.json` |
| L5 Gradio UI | #17 | `src/receipts/ui/**`, `tests/test_ui*.py` |
| L6 landing page | #18 | its own repository; in here only ADR-0005's license bullet |

Frozen for all lanes: `src/receipts/contracts.py`, `src/receipts/settings.py`, `src/receipts/fakes/**`, `tests/conftest.py`, `pyproject.toml`, `uv.lock`. A lane that needs a change stops and asks.

## Consequences

- A type error in `src/receipts/ui/` that strict mode would catch is not caught; the sabotage check in the W0 brief (`def f(x): return x` is red in `contracts.py` and green in `ui/app.py`) records that gap on purpose.
- On or before 2026-11-30 the repository owner removes every `--ignore-vuln` flag from `security.yml:37` or re-justifies it here. Today there are none to remove.
- Aceternity licence: recorded in ADR-0005 (PRs #21, #23, merged 2026-11-14) — permitted; the landing-page repository stays private.

## Alternatives considered

- `typeCheckingMode = "basic"` globally: rejected, it would relax every lane, not just the one that wraps an untyped library.
- A `paths:` filter or `continue-on-error` on the audit job: rejected, a gate that fires on some paths is green about the rest (AGENTS.md section 6).
- anyio's pytest plugin instead of pytest-asyncio: see above.
