"""L1: `load_pack` reads a YAML DomainPack and fails validation by field name."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from receipts.harness import load_pack

GOOD = """
id: pricing
display_name: Pricing
model: claude-sonnet-4-5
effort: medium
system_prompt: Compare published prices for {subject} and {rival}.
query_templates:
  - "{subject} pricing"
  - "{rival} pricing"
max_searches: 2
max_fetches: 3
"""


def test_load_pack_reads_yaml_from_the_given_root(tmp_path: Path) -> None:
    (tmp_path / "pricing.yaml").write_text(GOOD, encoding="utf-8")
    pack = load_pack("pricing", root=tmp_path)
    assert pack.id == "pricing"
    assert pack.effort == "medium"
    assert (pack.max_searches, pack.max_fetches, pack.timeout_s) == (2, 3, 120)


def test_load_pack_bad_field_fails_validation_naming_the_field(tmp_path: Path) -> None:
    (tmp_path / "pricing.yaml").write_text(
        GOOD.replace("max_searches: 2", "max_searches: lots"), encoding="utf-8"
    )
    with pytest.raises(ValidationError) as excinfo:
        load_pack("pricing", root=tmp_path)
    assert "max_searches" in str(excinfo.value)


def test_load_pack_missing_file_names_the_pack(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="nope"):
        load_pack("nope", root=tmp_path)
