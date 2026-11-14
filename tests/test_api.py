import pytest
from fastapi.testclient import TestClient

from receipts.api.app import create_app


@pytest.fixture
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


def test_echo_returns_the_message_and_its_length(client: TestClient) -> None:
    assert client.post("/echo", json={"message": "hi"}).json() == {"message": "hi", "length": 2}


@pytest.mark.parametrize("body", [{}, {"message": ""}, {"message": "x", "extra": 1}])
def test_echo_rejects_invalid_bodies(client: TestClient, body: dict[str, object]) -> None:
    assert client.post("/echo", json=body).status_code == 422
