from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import REPO_ROOT
from app.models import Run, RunStatus
from app.projects import tree
from app.projects.tree import MAX_ENTRIES, MAX_FILE_CHARS

COUNTER = REPO_ROOT / "content" / "exercises" / "counter-4bit"


def create(client: TestClient, **body: Any) -> dict[str, Any]:
    body.setdefault("name", "Coba")
    if "template" not in body and "exercise_id" not in body:
        body["template"] = "empty"
    r = client.post("/api/projects", json=body)
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


def entries(client: TestClient, pid: int) -> list[tuple[str, str]]:
    detail = client.get(f"/api/projects/{pid}").json()
    return [(e["path"], e["kind"]) for e in detail["entries"]]


def read(client: TestClient, pid: int, path: str) -> str:
    r = client.get(f"/api/projects/{pid}/files/{path}")
    assert r.status_code == 200, r.text
    return r.json()["content"]  # type: ignore[no-any-return]


class TestTemplates:
    def test_lists_templates(self, client: TestClient) -> None:
        ids = [t["id"] for t in client.get("/api/project-templates").json()]
        assert ids[:2] == ["empty", "cocotb-basic"]

    def test_empty_template(self, client: TestClient) -> None:
        p = create(client, name="  Proyek kosong  ", template="empty")

        assert p["name"] == "Proyek kosong"
        assert p["kind"] == "sandbox"
        assert p["source"] == "template:empty"
        assert ("smartx.yaml", "file") in [(e["path"], e["kind"]) for e in p["entries"]]

    def test_cocotb_basic_has_design_and_testbench(self, client: TestClient) -> None:
        p = create(client, template="cocotb-basic")

        paths = entries(client, p["id"])
        assert ("src", "dir") in paths
        assert ("test", "dir") in paths
        assert any(path.startswith("src/") and path.endswith(".v") for path, _ in paths)
        test_files = [path for path, _ in paths if path.startswith("test/test_")]
        assert test_files
        assert "import cocotb" in read(client, p["id"], test_files[0])

    def test_unknown_template(self, client: TestClient) -> None:
        r = client.post("/api/projects", json={"name": "x", "template": "tidak-ada"})
        assert r.status_code == 404


class TestFromExercise:
    def test_copies_starter_testbench_and_statement(self, client: TestClient) -> None:
        p = create(client, exercise_id="counter-4bit")

        assert p["source"] == "exercise:counter-4bit"
        assert p["name"] == "Coba"
        starter = (COUNTER / "starter.v").read_text(encoding="utf-8")
        assert read(client, p["id"], "src/counter4.v") == starter
        test = (COUNTER / "test_counter4.py").read_text(encoding="utf-8")
        assert read(client, p["id"], "test/test_counter4.py") == test
        assert "counter4" in read(client, p["id"], "smartx.yaml")
        assert read(client, p["id"], "README.md").strip()

    def test_uses_the_last_saved_code(self, client: TestClient) -> None:
        mine = "module counter4(input clk); // punyaku\nendmodule\n"
        assert (
            client.put("/api/exercises/counter-4bit/code", json={"code": mine}).status_code == 204
        )

        p = create(client, exercise_id="counter-4bit")

        assert read(client, p["id"], "src/counter4.v") == mine

    def test_never_copies_the_solution(self, client: TestClient) -> None:
        p = create(client, exercise_id="counter-4bit")

        solution = (COUNTER / "solution.v").read_text(encoding="utf-8")
        for path, kind in entries(client, p["id"]):
            assert "solution" not in path
            if kind == "file":
                assert read(client, p["id"], path) != solution
                assert "q <= q + 4'd1" not in read(client, p["id"], path)

    def test_unknown_exercise(self, client: TestClient) -> None:
        r = client.post("/api/projects", json={"name": "x", "exercise_id": "tidak-ada"})
        assert r.status_code == 404


class TestCreateValidation:
    @pytest.mark.parametrize(
        "body",
        [
            {"name": "", "template": "empty"},
            {"name": "   ", "template": "empty"},
            {"name": "x" * 81, "template": "empty"},
            {"name": "x"},  # neither template nor exercise
            {"name": "x", "template": "empty", "exercise_id": "counter-4bit"},
            {"name": "x", "exercise_id": "../counter-4bit"},
        ],
    )
    def test_rejects(self, client: TestClient, body: dict[str, Any]) -> None:
        assert client.post("/api/projects", json=body).status_code == 422


class TestProjects:
    def test_list_rename_delete(self, client: TestClient) -> None:
        a = create(client, name="A")
        b = create(client, name="B", template="cocotb-basic")

        listed = client.get("/api/projects").json()
        assert [p["name"] for p in listed] == ["B", "A"]  # newest first
        assert listed[0]["file_count"] > listed[1]["file_count"] >= 1

        r = client.patch(f"/api/projects/{a['id']}", json={"name": "A baru"})
        assert r.status_code == 200 and r.json()["name"] == "A baru"

        assert client.delete(f"/api/projects/{b['id']}").status_code == 204
        assert client.get(f"/api/projects/{b['id']}").status_code == 404
        assert client.get(f"/api/projects/{b['id']}/files/smartx.yaml").status_code == 404
        assert [p["name"] for p in client.get("/api/projects").json()] == ["A baru"]

    def test_delete_removes_finished_runs(self, client: TestClient) -> None:
        p = create(client)
        engine = client.app.state.engine  # type: ignore[attr-defined]
        with Session(engine) as s:
            run = Run(project_id=p["id"], kind="sim", status=RunStatus.succeeded)
            s.add(run)
            s.commit()
            run_id = run.id

        assert client.delete(f"/api/projects/{p['id']}").status_code == 204
        assert client.get(f"/api/runs/{run_id}").status_code == 404

    def test_cannot_delete_with_an_active_run(self, client: TestClient) -> None:
        p = create(client)
        engine = client.app.state.engine  # type: ignore[attr-defined]
        with Session(engine) as s:
            s.add(Run(project_id=p["id"], kind="sim", status=RunStatus.running))
            s.commit()

        r = client.delete(f"/api/projects/{p['id']}")
        assert r.status_code == 409
        assert "berjalan" in r.json()["detail"]

    def test_missing_project(self, client: TestClient) -> None:
        assert client.get("/api/projects/999").status_code == 404
        assert client.delete("/api/projects/999").status_code == 404
        assert client.put("/api/projects/999/files/a.v", json={"content": ""}).status_code == 404


class TestFiles:
    def test_create_read_update(self, client: TestClient) -> None:
        pid = create(client)["id"]

        r = client.post(f"/api/projects/{pid}/files", json={"path": "rtl/core/alu.v"})
        assert r.status_code == 201
        assert r.json() == {
            "path": "rtl/core/alu.v",
            "content": "",
            "updated_at": r.json()["updated_at"],
        }
        # Parent folders appear in the tree.
        assert ("rtl", "dir") in entries(client, pid)
        assert ("rtl/core", "dir") in entries(client, pid)

        r = client.put(f"/api/projects/{pid}/files/rtl/core/alu.v", json={"content": "module alu;"})
        assert r.status_code == 200
        assert read(client, pid, "rtl/core/alu.v") == "module alu;"

    def test_put_creates_missing_files(self, client: TestClient) -> None:
        pid = create(client)["id"]
        assert (
            client.put(f"/api/projects/{pid}/files/new.v", json={"content": "x"}).status_code == 200
        )
        assert read(client, pid, "new.v") == "x"

    def test_create_refuses_existing_paths(self, client: TestClient) -> None:
        pid = create(client)["id"]
        client.post(f"/api/projects/{pid}/files", json={"path": "src/a.v"})

        for path in ["src/a.v", "SRC/A.V", "src"]:  # also a clash on a case-insensitive disk
            r = client.post(f"/api/projects/{pid}/files", json={"path": path})
            assert r.status_code == 409, path
        # A file cannot be used as a folder.
        assert (
            client.post(f"/api/projects/{pid}/files", json={"path": "src/a.v/b.v"}).status_code
            == 409
        )
        assert (
            client.post(f"/api/projects/{pid}/folders", json={"path": "src/a.v/x"}).status_code
            == 409
        )

    @pytest.mark.parametrize(
        "path", ["../x.v", "/etc/passwd", "src\\x.v", "con.v", ".env", "a//b.v"]
    )
    def test_rejects_unsafe_paths(self, client: TestClient, path: str) -> None:
        pid = create(client)["id"]
        r = client.post(f"/api/projects/{pid}/files", json={"path": path})
        assert r.status_code == 422
        assert r.json()["detail"]  # a readable reason

    @pytest.mark.parametrize("path", ["..%2Fx.v", "%2E%2E/x.v", "src/..%2F..%2Fx.v", "con.v"])
    def test_rejects_unsafe_url_paths(self, client: TestClient, path: str) -> None:
        pid = create(client)["id"]
        assert client.put(
            f"/api/projects/{pid}/files/{path}", json={"content": ""}
        ).status_code in (
            404,
            422,
        )
        assert client.get(f"/api/projects/{pid}/files/{path}").status_code in (404, 422)

    def test_files_belong_to_their_project(self, client: TestClient) -> None:
        a = create(client)["id"]
        b = create(client)["id"]
        client.put(f"/api/projects/{a}/files/only-a.v", json={"content": "a"})

        assert client.get(f"/api/projects/{b}/files/only-a.v").status_code == 404

    def test_reading_a_folder_is_not_found(self, client: TestClient) -> None:
        pid = create(client)["id"]
        client.post(f"/api/projects/{pid}/folders", json={"path": "src"})
        assert client.get(f"/api/projects/{pid}/files/src").status_code == 404

    def test_file_size_limit(self, client: TestClient) -> None:
        pid = create(client)["id"]
        big = "x" * (MAX_FILE_CHARS + 1)
        assert (
            client.put(f"/api/projects/{pid}/files/big.v", json={"content": big}).status_code == 422
        )

    def test_entry_limit(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        assert MAX_ENTRIES >= 300
        monkeypatch.setattr(tree, "MAX_ENTRIES", 6)  # same code path, fewer requests
        pid = create(client)["id"]
        existing = len(entries(client, pid))
        for i in range(6 - existing):
            r = client.post(f"/api/projects/{pid}/files", json={"path": f"f{i}.v"})
            assert r.status_code == 201, r.text

        r = client.post(f"/api/projects/{pid}/files", json={"path": "satu-lagi.v"})
        assert r.status_code == 422
        assert "6" in r.json()["detail"]
        # A new folder that would also need a new parent counts both.
        assert client.post(f"/api/projects/{pid}/folders", json={"path": "a/b"}).status_code == 422


class TestFolders:
    def test_empty_folder_survives(self, client: TestClient) -> None:
        pid = create(client)["id"]
        assert (
            client.post(f"/api/projects/{pid}/folders", json={"path": "docs/notes"}).status_code
            == 201
        )
        assert ("docs", "dir") in entries(client, pid)
        assert ("docs/notes", "dir") in entries(client, pid)
        assert client.post(f"/api/projects/{pid}/folders", json={"path": "docs"}).status_code == 409

    def test_deleting_the_last_file_keeps_the_folder(self, client: TestClient) -> None:
        pid = create(client)["id"]
        client.put(f"/api/projects/{pid}/files/src/a.v", json={"content": ""})

        assert client.delete(f"/api/projects/{pid}/files/src/a.v").status_code == 204
        assert ("src", "dir") in entries(client, pid)
        assert ("src/a.v", "file") not in entries(client, pid)

    def test_delete_folder_is_recursive(self, client: TestClient) -> None:
        pid = create(client)["id"]
        client.put(f"/api/projects/{pid}/files/src/a.v", json={"content": ""})
        client.put(f"/api/projects/{pid}/files/src/sub/b.v", json={"content": ""})
        client.put(f"/api/projects/{pid}/files/src2/c.v", json={"content": ""})

        assert client.delete(f"/api/projects/{pid}/files/src").status_code == 204

        paths = [p for p, _ in entries(client, pid)]
        assert not any(p == "src" or p.startswith("src/") for p in paths)
        assert "src2/c.v" in paths  # a sibling with a common prefix is untouched

    def test_delete_missing(self, client: TestClient) -> None:
        pid = create(client)["id"]
        assert client.delete(f"/api/projects/{pid}/files/nope.v").status_code == 404


class TestMove:
    def move(self, client: TestClient, pid: int, src: str, dst: str) -> Any:
        return client.post(f"/api/projects/{pid}/move", json={"from_path": src, "to_path": dst})

    def test_rename_file_keeps_content(self, client: TestClient) -> None:
        pid = create(client)["id"]
        client.put(f"/api/projects/{pid}/files/a.v", json={"content": "isi"})

        r = self.move(client, pid, "a.v", "rtl/b.v")

        assert r.status_code == 200
        assert read(client, pid, "rtl/b.v") == "isi"
        assert client.get(f"/api/projects/{pid}/files/a.v").status_code == 404
        assert ("rtl", "dir") in [(e["path"], e["kind"]) for e in r.json()["entries"]]

    def test_case_only_rename(self, client: TestClient) -> None:
        pid = create(client)["id"]
        client.put(f"/api/projects/{pid}/files/alu.v", json={"content": "x"})
        assert self.move(client, pid, "alu.v", "ALU.v").status_code == 200
        assert read(client, pid, "ALU.v") == "x"

    def test_rename_folder_moves_everything_inside(self, client: TestClient) -> None:
        pid = create(client)["id"]
        client.put(f"/api/projects/{pid}/files/src/a.v", json={"content": "a"})
        client.post(f"/api/projects/{pid}/folders", json={"path": "src/empty"})
        client.put(f"/api/projects/{pid}/files/src2/c.v", json={"content": "c"})

        assert self.move(client, pid, "src", "rtl").status_code == 200

        paths = entries(client, pid)
        assert ("rtl/a.v", "file") in paths
        assert ("rtl/empty", "dir") in paths
        assert ("src2/c.v", "file") in paths
        assert not any(p == "src" or p.startswith("src/") for p, _ in paths)

    def test_conflicts(self, client: TestClient) -> None:
        pid = create(client)["id"]
        client.put(f"/api/projects/{pid}/files/src/a.v", json={"content": ""})
        client.put(f"/api/projects/{pid}/files/b.v", json={"content": ""})

        assert self.move(client, pid, "b.v", "src/a.v").status_code == 409
        assert self.move(client, pid, "b.v", "SRC").status_code == 409
        assert self.move(client, pid, "src", "src/inner").status_code == 409  # into itself
        assert self.move(client, pid, "missing.v", "c.v").status_code == 404
        assert self.move(client, pid, "b.v", "../b.v").status_code == 422


class TestConfig:
    def test_reads_the_template_config(self, client: TestClient) -> None:
        pid = create(client, template="cocotb-basic")["id"]

        r = client.get(f"/api/projects/{pid}/config")

        assert r.status_code == 200
        body = r.json()
        assert body["text"] == read(client, pid, "smartx.yaml")
        assert body["config"]["top"] == "counter"
        assert body["config"]["tests"] == ["test/test_counter.py"]
        assert body["sources"] == ["src/counter.v"]
        assert body["problems"] == []

    def test_reports_problems_with_lines(self, client: TestClient) -> None:
        pid = create(client, template="cocotb-basic")["id"]
        client.put(
            f"/api/projects/{pid}/files/smartx.yaml",
            json={"content": "top: counter\nsimulator: modelsim\n"},
        )

        body = client.get(f"/api/projects/{pid}/config").json()

        assert body["config"] is None
        assert body["text"].startswith("top: counter")
        (problem,) = body["problems"]
        assert problem["severity"] == "error"
        assert problem["line"] == 2

    def test_missing_config_file(self, client: TestClient) -> None:
        pid = create(client)["id"]
        client.delete(f"/api/projects/{pid}/files/smartx.yaml")

        body = client.get(f"/api/projects/{pid}/config").json()

        assert body["text"] == ""
        assert body["config"] is None
        assert "smartx.yaml" in body["problems"][0]["message"]

    def test_form_save_writes_yaml(self, client: TestClient) -> None:
        pid = create(client, template="cocotb-basic")["id"]
        config = {
            "top": "counter",
            "sources": ["src/**/*.v"],
            "tests": ["test/test_counter.py"],
            "simulator": "verilator",
            "parameters": {"WIDTH": 8},
            "defines": {"SIM": 1},
        }

        r = client.put(f"/api/projects/{pid}/config", json=config)

        assert r.status_code == 200
        assert r.json()["config"] == config
        text = read(client, pid, "smartx.yaml")
        assert "simulator: verilator" in text
        assert "WIDTH: 8" in text
        assert r.json()["text"] == text

    def test_check_does_not_save(self, client: TestClient) -> None:
        pid = create(client, template="cocotb-basic")["id"]
        before = read(client, pid, "smartx.yaml")

        r = client.post(
            f"/api/projects/{pid}/config/check",
            json={"text": "top: counter\nsources: [rtl/*.v]\ntests: [test/test_counter.py]\n"},
        )

        assert r.status_code == 200
        body = r.json()
        assert body["config"]["sources"] == ["rtl/*.v"]
        assert body["sources"] == []
        assert [p["severity"] for p in body["problems"]] == ["warning", "warning"]
        assert read(client, pid, "smartx.yaml") == before

    def test_check_size_limit(self, client: TestClient) -> None:
        pid = create(client)["id"]
        r = client.post(
            f"/api/projects/{pid}/config/check", json={"text": "x" * (MAX_FILE_CHARS + 1)}
        )
        assert r.status_code == 422

    @pytest.mark.parametrize(
        "config",
        [
            {"top": "9bad"},
            {"top": "a", "simulator": "questa"},
            {"top": "a", "sources": ["../x.v"]},
            {"top": "a", "parameters": {"W": True}},
            {"top": "a", "unknown": 1},
        ],
    )
    def test_form_save_rejects_invalid(self, client: TestClient, config: dict[str, Any]) -> None:
        pid = create(client)["id"]
        before = read(client, pid, "smartx.yaml")

        assert client.put(f"/api/projects/{pid}/config", json=config).status_code == 422
        assert read(client, pid, "smartx.yaml") == before


def test_every_template_and_exercise_copy_has_a_valid_config(client: TestClient) -> None:
    ids = [t["id"] for t in client.get("/api/project-templates").json()]
    projects = [create(client, template=t) for t in ids]
    projects.append(create(client, exercise_id="counter-4bit"))

    for p in projects:
        body = client.get(f"/api/projects/{p['id']}/config").json()
        assert body["config"] is not None, (p["source"], body["problems"])
        errors = [x for x in body["problems"] if x["severity"] == "error"]
        assert errors == [], p["source"]
        assert body["sources"], p["source"]
        if p["source"] != "template:empty":
            assert body["problems"] == [], (p["source"], body["problems"])
