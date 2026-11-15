import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "docs" / "api" / "openapi.json"


def _load_script() -> ModuleType:
    script = ROOT / "scripts" / "export_openapi.py"
    spec = importlib.util.spec_from_file_location("export_openapi", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_export_writes_a_document_with_every_route(tmp_path: Path) -> None:
    module = _load_script()
    out = tmp_path / "openapi.json"
    assert module.main([str(out)]) == 0
    doc = json.loads(out.read_text())
    assert doc["info"]["title"] == "Receipts"
    assert {"/healthz", "/api/runs", "/api/runs/{run_id}"} <= set(doc["paths"])
    assert "/echo" not in doc["paths"]
    assert "post" in doc["paths"]["/api/runs"] and "get" in doc["paths"]["/api/runs"]


def test_committed_document_matches_a_fresh_export(tmp_path: Path) -> None:
    """`uv run python scripts/export_openapi.py` was run after the last API change."""
    module = _load_script()
    out = tmp_path / "openapi.json"
    assert module.main([str(out)]) == 0
    assert COMMITTED.exists(), f"{COMMITTED} is missing: run scripts/export_openapi.py"
    assert json.loads(COMMITTED.read_text()) == json.loads(out.read_text())
