from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import __version__, docker_probe
from app.config import Settings
from app.docker_probe import DockerStatus, probe_docker


def test_health_reports_version_and_docker(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["docker"] == {
        "available": True,
        "server_version": "29.0.0-test",
        "error": None,
    }


@pytest.mark.parametrize(
    "docker_status",
    [DockerStatus(available=False, error="Docker tidak bisa dihubungi: boom")],
)
def test_health_is_ok_when_docker_is_down(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["docker"]["available"] is False
    assert "boom" in r.json()["docker"]["error"]


def test_startup_creates_database(client: TestClient, settings: Settings) -> None:
    assert settings.db_path.is_file()


def test_probe_docker_handles_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(**_: Any) -> None:
        raise OSError("pipe not found")

    monkeypatch.setattr(docker_probe.docker, "from_env", fail)
    status = probe_docker()
    assert status.available is False
    assert status.error is not None
    assert "pipe not found" in status.error


def test_probe_docker_reports_server_version(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def version(self) -> dict[str, str]:
            return {"Version": "29.8.2"}

        def close(self) -> None:
            pass

    monkeypatch.setattr(docker_probe.docker, "from_env", lambda **_: FakeClient())
    assert probe_docker() == DockerStatus(available=True, server_version="29.8.2")
