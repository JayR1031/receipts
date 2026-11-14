"""Write the OpenAPI document, so a change to the API shape shows up as a diff in review."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from receipts.api.app import create_app


def main(argv: list[str]) -> int:
    out = Path(argv[0]) if argv else Path("docs/api/openapi.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = json.dumps(create_app().openapi(), indent=2, sort_keys=True)
    out.write_text(doc + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
