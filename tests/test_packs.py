"""Domain packs: schema validity, template safety, and that the YAML ships in the package."""

from __future__ import annotations

from importlib import resources

import pytest
import yaml

from receipts.contracts import DomainPack

PACK_IDS = ["positioning_seo", "pricing"]


def _pack_files() -> list[str]:
    root = resources.files("receipts.packs")
    return sorted(p.name for p in root.iterdir() if p.name.endswith(".yaml"))


def _load(pack_id: str) -> DomainPack:
    text = resources.files("receipts.packs").joinpath(f"{pack_id}.yaml").read_text("utf-8")
    return DomainPack.model_validate(yaml.safe_load(text))


def test_exactly_the_two_packs_ship() -> None:
    assert _pack_files() == [f"{p}.yaml" for p in PACK_IDS]


@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_pack_validates_and_matches_filename(pack_id: str) -> None:
    pack = _load(pack_id)
    assert pack.id == pack_id
    assert pack.model == "claude-sonnet-5-5"
    assert pack.effort is not None
    assert pack.system_prompt.strip()
    assert pack.rubric.strip()
    assert pack.max_searches > 0
    assert pack.max_fetches > 0
    assert pack.timeout_s > 0


@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_query_templates_format_cleanly(pack_id: str) -> None:
    pack = _load(pack_id)
    assert 3 <= len(pack.query_templates) <= 4
    for template in pack.query_templates:
        out = template.format(subject="Acme", rival="Bolt", category="widgets")
        assert "{" not in out
        assert "}" not in out
        assert out.strip()
