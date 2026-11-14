import pytest
from fastapi.testclient import TestClient

from receipts.api.app import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def test_healthz_reports_the_build_sha(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_SHA", "abc1234")
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "sha": "abc1234", "version": "0.1.0"}


def test_healthz_says_unknown_without_a_sha(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GIT_SHA", raising=False)
    assert client.get("/healthz").json()["sha"] == "unknown"


def test_root_redirects_to_the_ui(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/ui"


def test_ui_is_mounted(client: TestClient) -> None:
    assert client.get("/ui").status_code == 200


def test_echo_is_gone(client: TestClient) -> None:
    assert client.post("/echo", json={"message": "hi"}).status_code == 404
