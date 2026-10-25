import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from docker.errors import NotFound
from pydantic import ValidationError

from app.config import Settings
from app.jobs.docker_runner import DockerRunner, default_job_user, host_path
from app.jobs.runner import ContainerSpec, JobClass, JobHandle, LineSplitter


class FakeImage:
    id = "sha256:abc"


class FakeContainer:
    def __init__(self, chunks: list[bytes] | None = None, exit_code: int = 0) -> None:
        self.id = "c0ffee"
        self.image = FakeImage()
        self.chunks = chunks or []
        self.exit_code = exit_code
        self.killed = False
        self.removed = False

    def logs(self, **kwargs: Any) -> Iterator[bytes]:
        assert kwargs == {"stream": True, "follow": True, "stdout": True, "stderr": True}
        return iter(self.chunks)

    def wait(self) -> dict[str, int]:
        return {"StatusCode": self.exit_code}

    def kill(self) -> None:
        self.killed = True

    def remove(self, force: bool = False) -> None:
        assert force
        self.removed = True


class FakeContainers:
    def __init__(self, container: FakeContainer) -> None:
        self.container = container
        self.run_kwargs: dict[str, Any] = {}
        self.list_kwargs: dict[str, Any] = {}

    def run(self, **kwargs: Any) -> FakeContainer:
        self.run_kwargs = kwargs
        return self.container

    def get(self, container_id: str) -> FakeContainer:
        if self.container.removed:
            raise NotFound("gone")
        assert container_id == self.container.id
        return self.container

    def list(self, **kwargs: Any) -> list[FakeContainer]:
        self.list_kwargs = kwargs
        return [self.container]


class FakeClient:
    def __init__(self, container: FakeContainer) -> None:
        self.containers = FakeContainers(container)


@pytest.fixture
def container() -> FakeContainer:
    return FakeContainer()


@pytest.fixture
def client(container: FakeContainer) -> FakeClient:
    return FakeClient(container)


def make_runner(settings: Settings, client: FakeClient) -> DockerRunner:
    return DockerRunner(settings, client_factory=lambda timeout: client)


def run_dir(settings: Settings, run_id: str = "r1") -> Path:
    d = settings.runs_dir / run_id
    d.mkdir(parents=True)
    return d


async def test_start_applies_all_limits(settings: Settings, client: FakeClient) -> None:
    settings = settings.model_copy(update={"job_user": "1000:1000"})
    runner = make_runner(settings, client)
    rd = run_dir(settings)

    handle = await runner.start("r1", rd, ContainerSpec(command=["yosys", "-V"]))

    kw = client.containers.run_kwargs
    assert kw["image"] == "smartx/toolchain:local"
    assert kw["command"] == ["yosys", "-V"]
    assert kw["detach"] is True
    assert kw["network_mode"] == "none"
    assert kw["user"] == "1000:1000"
    assert kw["mem_limit"] == "4g"
    assert kw["memswap_limit"] == "4g"
    assert kw["nano_cpus"] == 2_000_000_000
    assert kw["pids_limit"] == 512
    assert kw["cap_drop"] == ["ALL"]
    assert kw["security_opt"] == ["no-new-privileges"]
    assert kw["working_dir"] == "/work"
    assert kw["labels"] == {"smartx.run_id": "r1"}
    assert kw["volumes"] == {
        str(rd): {"bind": "/work", "mode": "rw"},
        str(settings.content_dir): {"bind": "/content", "mode": "ro"},
    }
    assert "privileged" not in kw
    assert not any("docker.sock" in src for src in kw["volumes"])
    assert handle == JobHandle(
        run_id="r1", container_id="c0ffee", image="smartx/toolchain:local", image_id="sha256:abc"
    )


async def test_heavy_jobs_use_asic_image_and_limits(settings: Settings, client: FakeClient) -> None:
    settings = settings.model_copy(update={"asic_image": "asic:1.0"})
    runner = make_runner(settings, client)
    spec = ContainerSpec(command=["true"], job_class=JobClass.heavy, mount_content=False)

    await runner.start("r1", run_dir(settings), spec)

    kw = client.containers.run_kwargs
    assert kw["image"] == "asic:1.0"
    assert kw["mem_limit"] == "12g"
    assert kw["nano_cpus"] == 4_000_000_000
    assert len(kw["volumes"]) == 1


async def test_heavy_job_without_asic_image_fails(settings: Settings, client: FakeClient) -> None:
    runner = make_runner(settings, client)
    spec = ContainerSpec(command=["true"], job_class=JobClass.heavy)
    with pytest.raises(RuntimeError, match="ASIC_IMAGE"):
        await runner.start("r1", run_dir(settings), spec)


async def test_host_paths_are_used_for_mounts(settings: Settings, client: FakeClient) -> None:
    settings = settings.model_copy(
        update={"host_data_dir": "C:/smartx/data", "host_content_dir": "C:/smartx/content"}
    )
    runner = make_runner(settings, client)

    await runner.start("r1", run_dir(settings), ContainerSpec(command=["true"]))

    assert client.containers.run_kwargs["volumes"] == {
        "C:/smartx/data/runs/r1": {"bind": "/work", "mode": "rw"},
        "C:/smartx/content": {"bind": "/content", "mode": "ro"},
    }


def test_host_path_rejects_paths_outside_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        host_path(tmp_path / "other", tmp_path / "data", "/host/data")


async def test_stream_wait_kill_cleanup(settings: Settings, container: FakeContainer) -> None:
    container.chunks = [b"Yosys 0.7", b"0\nline2\n", b"tail"]
    container.exit_code = 3
    client = FakeClient(container)
    runner = make_runner(settings, client)
    handle = await runner.start("r1", run_dir(settings), ContainerSpec(command=["true"]))

    lines = [line async for line in runner.stream_logs(handle)]
    assert lines == ["Yosys 0.70", "line2", "tail"]
    assert await runner.wait(handle) == 3

    await runner.kill(handle)
    assert container.killed
    await runner.cleanup(handle)
    assert container.removed
    # Both are no-ops once the container is gone.
    await runner.kill(handle)
    await runner.cleanup(handle)


async def test_remove_orphans(settings: Settings, client: FakeClient) -> None:
    runner = make_runner(settings, client)
    assert await runner.remove_orphans() == 1
    assert client.containers.list_kwargs == {"all": True, "filters": {"label": "smartx.run_id"}}
    assert client.containers.container.removed


class TestJobUser:
    def test_uses_backend_uid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(os, "getuid", lambda: 1001, raising=False)
        monkeypatch.setattr(os, "getgid", lambda: 1002, raising=False)
        assert default_job_user() == "1001:1002"

    def test_never_root_when_backend_runs_as_root(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(os, "getuid", lambda: 0, raising=False)
        monkeypatch.setattr(os, "getgid", lambda: 0, raising=False)
        assert default_job_user() == "1000:1000"

    def test_windows_has_no_getuid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delattr(os, "getuid", raising=False)
        assert default_job_user() == "1000:1000"

    @pytest.mark.parametrize("bad", ["0:0", "0", "root", "1000", "abc:def", "1000:0x1"])
    def test_settings_reject_root_or_malformed_user(self, bad: str) -> None:
        with pytest.raises(ValidationError):
            Settings(_env_file=None, job_user=bad)

    async def test_run_dir_is_handed_to_job_user_when_root(
        self, monkeypatch: pytest.MonkeyPatch, settings: Settings, client: FakeClient
    ) -> None:
        chowned: list[tuple[Path, int, int]] = []
        monkeypatch.setattr(os, "geteuid", lambda: 0, raising=False)
        monkeypatch.setattr(os, "chown", lambda p, u, g: chowned.append((p, u, g)), raising=False)
        settings = settings.model_copy(update={"job_user": "1001:1002"})
        rd = run_dir(settings)

        await make_runner(settings, client).start("r1", rd, ContainerSpec(command=["true"]))

        assert chowned == [(rd, 1001, 1002)]
        assert client.containers.run_kwargs["user"] == "1001:1002"


def test_line_splitter_handles_split_utf8() -> None:
    s = LineSplitter()
    data = "héllo\r\nwörld".encode()
    out: list[str] = []
    for i in range(len(data)):
        out += s.feed(data[i : i + 1])
    out += s.flush()
    assert out == ["héllo", "wörld"]
