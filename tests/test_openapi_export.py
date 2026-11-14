import importlib.util
import json
from pathlib import Path


def test_export_writes_a_document_with_every_route(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "export_openapi.py"
    spec = importlib.util.spec_from_file_location("export_openapi", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = tmp_path / "openapi.json"
    assert module.main([str(out)]) == 0
    doc = json.loads(out.read_text())
    assert doc["info"]["title"] == "Receipts"
    assert {"/healthz", "/echo"} <= set(doc["paths"])
