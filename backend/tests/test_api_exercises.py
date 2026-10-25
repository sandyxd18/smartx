from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.jobs.fake_runner import FakeJob, FakeRunner
from app.main import create_app
from tests.helpers import TERMINAL, wait_for_status, write_exercise

FIXTURES = Path(__file__).parent / "fixtures" / "runs"
SECRET = "SECRET_SOLUTION_MARKER"
CODE = "module top; /* my attempt */ endmodule\n"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    content = tmp_path / "content"
    a = write_exercise(content / "exercises", "ex-a", hints=["pakai always", "reset dulu"], order=1)
    (a / "README.md").write_text("# Soal A\n\n| Port | Arah |\n|---|---|\n", encoding="utf-8")
    (a / "starter.v").write_text("module top;\nendmodule\n", encoding="utf-8")
    (a / "solution.v").write_text(f"// {SECRET}\nmodule top; endmodule\n", encoding="utf-8")
    b = write_exercise(content / "exercises", "ex-b", step=2, topics=["fsm"], level=3)
    (b / "solution.v").write_text(f"// {SECRET}\n", encoding="utf-8")
    return Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        content_dir=content,
        content_auto_reload=False,
        solution_unlock_attempts=3,
    )


def make_client(settings: Settings, runner: FakeRunner) -> Iterator[TestClient]:
    with TestClient(create_app(settings, runner=runner)) as c:
        yield c


@pytest.fixture
def runner() -> FakeRunner:
    # Default: the grader reports failing tests (exit 1 + result.json).
    return FakeRunner(FakeJob(exit_code=1, fixture_dir=FIXTURES / "grade-fail"))


@pytest.fixture
def client(settings: Settings, runner: FakeRunner) -> Iterator[TestClient]:
    yield from make_client(settings, runner)


def submit(client: TestClient, ex_id: str = "ex-a", code: str = CODE) -> dict[str, Any]:
    r = client.post(f"/api/exercises/{ex_id}/runs", json={"code": code})
    assert r.status_code == 201, r.text
    return wait_for_status(client, r.json()["id"], TERMINAL)


def test_list_with_progress(client: TestClient) -> None:
    r = client.get("/api/exercises")

    assert r.status_code == 200
    assert SECRET not in r.text
    assert r.json() == [
        {
            "id": "ex-a",
            "title": "Soal ex-a",
            "step": 1,
            "level": 1,
            "topics": ["sequential"],
            "order": 1,
            "requires": [],
            "status": "not_started",
            "attempts": 0,
        },
        {
            "id": "ex-b",
            "title": "Soal ex-b",
            "step": 2,
            "level": 3,
            "topics": ["fsm"],
            "order": None,
            "requires": [],
            "status": "not_started",
            "attempts": 0,
        },
    ]


def test_detail_of_a_new_exercise(client: TestClient) -> None:
    r = client.get("/api/exercises/ex-a")

    assert r.status_code == 200
    assert SECRET not in r.text
    body = r.json()
    assert body["id"] == "ex-a"
    assert body["toplevel"] == "top"
    assert body["language"] == "verilog"
    assert body["statement"].startswith("# Soal A")
    assert body["starter"] == "module top;\nendmodule\n"
    assert body["code"] == body["starter"]
    assert body["hints"] == []
    assert body["hints_total"] == 2
    assert body["solution_available"] is False
    assert body["solution_unlock_attempts"] == 3
    assert body["last_run"] is None


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/exercises/nope"),
        ("POST", "/api/exercises/nope/runs"),
        ("POST", "/api/exercises/nope/hints/next"),
        ("GET", "/api/exercises/nope/solution"),
    ],
)
def test_unknown_exercise(client: TestClient, method: str, path: str) -> None:
    r = client.request(method, path, json={"code": CODE})
    assert r.status_code == 404
    assert r.json()["detail"] == "Soal tidak ditemukan."


def test_run_records_attempt_and_code(client: TestClient, runner: FakeRunner) -> None:
    run = submit(client)

    assert run["kind"] == "grade"
    assert run["params"]["exercise_id"] == "ex-a"
    assert run["status"] == "succeeded"
    assert run["result"]["status"] == "fail"
    assert SECRET not in str(run)

    detail = client.get("/api/exercises/ex-a").json()
    assert detail["code"] == CODE
    assert detail["attempts"] == 1
    assert detail["status"] == "attempted"
    assert detail["last_run"]["id"] == run["id"]
    # The other exercise is untouched.
    assert client.get("/api/exercises/ex-b").json()["last_run"] is None


def test_run_rejects_huge_code(client: TestClient) -> None:
    r = client.post("/api/exercises/ex-a/runs", json={"code": "x" * 200_001})
    assert r.status_code == 422


class TestSolution:
    def test_locked_at_first(self, client: TestClient) -> None:
        r = client.get("/api/exercises/ex-a/solution")
        assert r.status_code == 403
        assert SECRET not in r.text
        assert "3 percobaan" in r.json()["detail"]

    def test_unlocks_after_enough_attempts(self, client: TestClient) -> None:
        submit(client)
        submit(client)
        assert client.get("/api/exercises/ex-a/solution").status_code == 403

        submit(client)

        assert client.get("/api/exercises/ex-a").json()["solution_available"] is True
        r = client.get("/api/exercises/ex-a/solution")
        assert r.status_code == 200
        assert SECRET in r.json()["code"]
        # Unlocking one exercise does not unlock another.
        assert client.get("/api/exercises/ex-b/solution").status_code == 403


class TestPassing:
    @pytest.fixture
    def runner(self) -> FakeRunner:
        return FakeRunner(FakeJob(exit_code=0, fixture_dir=FIXTURES / "grade-pass"))

    def test_pass_marks_solved_and_unlocks_solution(self, client: TestClient) -> None:
        submit(client)

        summary = client.get("/api/exercises").json()[0]
        assert summary["status"] == "solved"
        assert summary["attempts"] == 1
        assert client.get("/api/exercises/ex-a/solution").status_code == 200


def test_solved_stays_solved_after_a_failing_run(settings: Settings) -> None:
    jobs = iter(
        [
            FakeJob(exit_code=0, fixture_dir=FIXTURES / "grade-pass"),
            FakeJob(exit_code=1, fixture_dir=FIXTURES / "grade-fail"),
        ]
    )
    runner = FakeRunner(lambda run_id, spec: next(jobs))
    for client in make_client(settings, runner):
        submit(client)
        submit(client, code="module top; broken")

        detail = client.get("/api/exercises/ex-a").json()
        assert detail["status"] == "solved"
        assert detail["attempts"] == 2
        assert detail["code"] == "module top; broken"


def test_broken_run_counts_as_attempt_but_not_solved(settings: Settings) -> None:
    runner = FakeRunner(FakeJob(exit_code=0))  # no result.json: collect() fails
    for client in make_client(settings, runner):
        run = submit(client)
        assert run["status"] == "failed"
        assert client.get("/api/exercises/ex-a").json()["status"] == "attempted"


def test_hints_open_one_by_one(client: TestClient) -> None:
    r1 = client.post("/api/exercises/ex-a/hints/next")
    assert r1.status_code == 200
    assert r1.json() == {"hints": ["pakai always"], "total": 2}

    r2 = client.post("/api/exercises/ex-a/hints/next")
    assert r2.json() == {"hints": ["pakai always", "reset dulu"], "total": 2}

    r3 = client.post("/api/exercises/ex-a/hints/next")  # nothing left: no-op
    assert r3.json() == {"hints": ["pakai always", "reset dulu"], "total": 2}

    assert client.get("/api/exercises/ex-a").json()["hints"] == ["pakai always", "reset dulu"]


def test_progress_survives_restart(settings: Settings, runner: FakeRunner) -> None:
    for client in make_client(settings, runner):
        submit(client)
        client.post("/api/exercises/ex-a/hints/next")

    for client in make_client(settings, FakeRunner()):
        detail = client.get("/api/exercises/ex-a").json()
        assert detail["attempts"] == 1
        assert detail["code"] == CODE
        assert detail["hints"] == ["pakai always"]
        assert detail["last_run"] is not None


class TestTypedRuns:
    def test_runs_carry_a_typed_grade_result(self, client: TestClient) -> None:
        r = client.post("/api/exercises/ex-a/runs", json={"code": CODE})
        assert r.status_code == 201
        created = r.json()
        assert created["grade"] is None  # not graded yet

        wait_for_status(client, created["id"], TERMINAL)
        run = client.get(f"/api/exercises/ex-a/runs/{created['id']}").json()

        assert run["id"] == created["id"]
        assert run["grade"]["status"] == "fail"
        assert [t["passed"] for t in run["grade"]["tests"]] == [False, False, False]
        assert run["grade"]["wave_url"].endswith("/build/sim_build/counter4.fst")
        assert client.get("/api/exercises/ex-a").json()["last_run"]["grade"]["status"] == "fail"

    def test_run_of_another_exercise_is_not_found(self, client: TestClient) -> None:
        run_id = submit(client, "ex-a")["id"]
        r = client.get(f"/api/exercises/ex-b/runs/{run_id}")
        assert r.status_code == 404
        assert r.json()["detail"] == "Run tidak ditemukan."

    def test_non_grade_run_is_not_found(self, client: TestClient) -> None:
        echo = client.post("/api/runs", json={"kind": "echo", "params": {}}).json()
        assert client.get(f"/api/exercises/ex-a/runs/{echo['id']}").status_code == 404
