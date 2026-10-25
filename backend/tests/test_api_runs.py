import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.jobs.fake_runner import FakeJob, FakeRunner
from tests.helpers import TERMINAL, wait_for_status


def create_echo(client: TestClient, **params: Any) -> dict[str, Any]:
    r = client.post("/api/runs", json={"kind": "echo", "params": params})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def runner() -> FakeRunner:
    return FakeRunner(FakeJob(logs=["Yosys 0.70+219 (fake)"]))


def test_create_and_get_run(client: TestClient) -> None:
    created = create_echo(client)
    assert created["kind"] == "echo"
    assert created["status"] in {"queued", "running", "succeeded"}
    assert len(created["id"]) == 32

    run = wait_for_status(client, created["id"], TERMINAL)
    assert run["status"] == "succeeded"
    assert run["result"] == {"yosys_version": "Yosys 0.70+219 (fake)"}
    assert run["exit_code"] == 0
    # Timestamps are serialized as UTC so the browser does not read them as local time.
    assert run["created_at"].endswith(("Z", "+00:00"))
    assert run["finished_at"].endswith(("Z", "+00:00"))


@pytest.mark.parametrize(
    "body",
    [
        {"kind": "rm-rf", "params": {}},
        {"kind": "echo", "params": {"sleep_s": -1}},
        {"kind": "echo", "params": {"command": "ls"}},
    ],
)
def test_create_rejects_bad_input(client: TestClient, body: dict[str, Any]) -> None:
    assert client.post("/api/runs", json=body).status_code == 422


def test_get_unknown_run(client: TestClient) -> None:
    r = client.get("/api/runs/" + "0" * 32)
    assert r.status_code == 404
    assert r.json()["detail"] == "Run tidak ditemukan."


class TestCancel:
    @pytest.fixture
    def runner(self) -> FakeRunner:
        return FakeRunner(FakeJob(block=True))

    def test_cancel_running_run(self, client: TestClient, runner: FakeRunner) -> None:
        run_id = create_echo(client, sleep_s=60)["id"]
        wait_for_status(client, run_id, {"running"})

        r = client.post(f"/api/runs/{run_id}/cancel")
        assert r.status_code == 202

        run = wait_for_status(client, run_id, TERMINAL)
        assert run["status"] == "cancelled"
        assert runner.killed == {run_id}
        assert runner.cleaned == {run_id}

    def test_cancel_finished_run_conflicts(self, client: TestClient) -> None:
        run_id = create_echo(client)["id"]
        client.post(f"/api/runs/{run_id}/cancel")
        wait_for_status(client, run_id, TERMINAL)

        r = client.post(f"/api/runs/{run_id}/cancel")
        assert r.status_code == 409

    def test_cancel_unknown_run(self, client: TestClient) -> None:
        assert client.post("/api/runs/" + "0" * 32 + "/cancel").status_code == 404


def test_events_stream_for_finished_run(client: TestClient) -> None:
    run_id = create_echo(client)["id"]
    wait_for_status(client, run_id, TERMINAL)

    with client.stream("GET", f"/api/runs/{run_id}/events") as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = r.read().decode()

    events = [
        (block.split("\n")[0], json.loads(block.split("\n")[1].removeprefix("data: ")))
        for block in body.replace("\r\n", "\n").strip().split("\n\n")
        if block.startswith("event:")
    ]
    assert events == [
        ("event: log", {"line": "Yosys 0.70+219 (fake)"}),
        ("event: status", {"status": "succeeded"}),
    ]


def test_events_for_unknown_run(client: TestClient) -> None:
    assert client.get("/api/runs/" + "0" * 32 + "/events").status_code == 404


class TestFiles:
    @pytest.fixture
    def run_id(self, client: TestClient, settings: Settings) -> str:
        run_id = create_echo(client)["id"]
        wait_for_status(client, run_id, TERMINAL)
        (settings.data_dir / "secret.txt").write_text("top secret")
        (settings.runs_dir / run_id / "waves").mkdir()
        (settings.runs_dir / run_id / "waves" / "dump.fst").write_bytes(b"\x00FST")
        return run_id

    def test_download_run_files(self, client: TestClient, run_id: str) -> None:
        r = client.get(f"/api/runs/{run_id}/files/run.log")
        assert r.status_code == 200
        assert r.text == "Yosys 0.70+219 (fake)\n"

        r = client.get(f"/api/runs/{run_id}/files/waves/dump.fst")
        assert r.status_code == 200
        assert r.content == b"\x00FST"

    def test_missing_file(self, client: TestClient, run_id: str) -> None:
        assert client.get(f"/api/runs/{run_id}/files/nope.txt").status_code == 404
        assert client.get(f"/api/runs/{run_id}/files/waves").status_code == 404

    @pytest.mark.parametrize(
        "raw_path",
        [
            "..%2Fsecret.txt",
            "..%2F..%2Fsecret.txt",
            "%2e%2e/%2e%2e/secret.txt",
            "waves%2F..%2F..%2F..%2Fsecret.txt",
            "..%5C..%5Csecret.txt",
            "%2Fetc%2Fpasswd",
            "C:%2FWindows%2Fwin.ini",
            "..%2F..%2Fsmartx.db",
            "run.log%00.png",
        ],
    )
    def test_path_traversal_is_rejected(
        self, client: TestClient, run_id: str, raw_path: str
    ) -> None:
        r = client.get(f"/api/runs/{run_id}/files/{raw_path}")
        assert r.status_code in (400, 404)
        assert b"top secret" not in r.content
        assert b"SQLite" not in r.content

    @pytest.mark.parametrize("bad_id", ["..", "..%2F..", "not-a-run-id"])
    def test_bad_run_id(self, client: TestClient, bad_id: str) -> None:
        r = client.get(f"/api/runs/{bad_id}/files/secret.txt")
        assert r.status_code in (400, 404, 422)
        assert b"top secret" not in r.content
