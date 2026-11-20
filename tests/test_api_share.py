"""`/share/{run_id}` and `/share/card.png` against the Wave 0 fakes. No network, no keys.

All text here is invented (the fakes' Acme Widgets vs Zeta Gadgets run).
"""

from __future__ import annotations

import httpx
import pytest

from receipts.api.app import create_app
from receipts.contracts import RunRequest
from receipts.fakes import FakeRunService

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _client(service: FakeRunService) -> httpx.AsyncClient:
    app = create_app()
    app.state.run_service = service
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://app.example")


async def test_a_finished_run_has_a_public_page_with_preview_tags(
    fake_run_service: FakeRunService,
) -> None:
    run_id = await fake_run_service.start(RunRequest(subject="Acme Widgets", rival="Zeta Gadgets"))
    async with _client(fake_run_service) as client:
        response = await client.get(f"/share/{run_id}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    page = response.text
    assert "<!doctype html>" in page
    assert '<meta property="og:title" content="Acme Widgets vs Zeta Gadgets: 2 of 3 claims' in page
    assert f'<meta property="og:url" content="https://app.example/share/{run_id}">' in page
    assert '<meta property="og:image" content="https://app.example/share/card.png">' in page
    assert '<meta name="twitter:card" content="summary_large_image">' in page
    assert '<meta name="robots" content="noindex">' in page
    assert 'aria-label="2 of 3 claims verified"' in page
    assert 'class="bc-share"' not in page  # the share page does not link to itself
    assert 'href="/ui/"' in page


async def test_an_unknown_run_is_a_404_page_not_json(fake_run_service: FakeRunService) -> None:
    async with _client(fake_run_service) as client:
        response = await client.get("/share/run-does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "Battlecard not found" in response.text


async def test_the_preview_image_is_a_cacheable_png(fake_run_service: FakeRunService) -> None:
    async with _client(fake_run_service) as client:
        response = await client.get("/share/card.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(PNG_MAGIC)
    assert "max-age" in response.headers["cache-control"]


@pytest.mark.parametrize("path", ["/share/{run_id}", "/share/card.png"])
async def test_share_routes_stay_out_of_the_openapi_document(path: str) -> None:
    assert path not in create_app().openapi()["paths"]
