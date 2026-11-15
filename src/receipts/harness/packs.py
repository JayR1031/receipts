"""Load a `DomainPack` from YAML. Packs ship inside the package (`receipts.packs`), so
`importlib.resources` finds them in the image too; tests point `root=` at a temp directory."""

from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable

import yaml

from receipts.contracts import DomainPack


def load_pack(name: str, *, root: Traversable | None = None) -> DomainPack:
    """Read `<name>.yaml` under `root` (default: the `receipts.packs` package) and validate it.

    A bad field raises `pydantic.ValidationError` naming the field; a missing file raises
    `FileNotFoundError` naming the pack.
    """
    base = files("receipts.packs") if root is None else root
    path = base / f"{name}.yaml"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"domain pack {name!r} not found at {path}") from exc
    raw: object = yaml.safe_load(text)
    return DomainPack.model_validate(raw)
