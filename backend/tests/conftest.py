from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.health import get_docker_probe
from app.config import Settings
from app.docker_probe import DockerStatus
from app.jobs.fake_runner import FakeRunner
from app.main import create_app


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # `make test` exports .env into the environment; tests must not depend on it.
    for field in Settings.model_fields.values():
        if isinstance(field.validation_alias, str):
            monkeypatch.delenv(field.validation_alias, raising=False)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # _env_file=None: tests must not depend on the developer's .env.
    return Settings(_env_file=None, data_dir=tmp_path / "data")


@pytest.fixture
def docker_status() -> DockerStatus:
    return DockerStatus(available=True, server_version="29.0.0-test")


@pytest.fixture
def runner() -> FakeRunner:
    return FakeRunner()


@pytest.fixture
def app(settings: Settings, docker_status: DockerStatus, runner: FakeRunner) -> FastAPI:
    app = create_app(settings, runner=runner)
    app.dependency_overrides[get_docker_probe] = lambda: lambda: docker_status
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
