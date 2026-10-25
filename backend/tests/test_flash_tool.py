"""tools/flash/smartx-flash against a stub backend (real HTTP, no board needed)."""

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.config import REPO_ROOT

SCRIPT = REPO_ROOT / "tools" / "flash" / "smartx-flash"
BITSTREAM = b"\x00\xffstand-in bitstream"
TANG = {"id": "tang-nano-9k", "flash_command": ["openFPGALoader", "-b", "tangnano9k"]}


def load_tool() -> ModuleType:
    loader = SourceFileLoader("smartx_flash", str(SCRIPT))
    spec = spec_from_loader("smartx_flash", loader)
    assert spec is not None
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


tool = load_tool()


def build(run_id: str, **overrides: Any) -> dict[str, Any]:
    return {
        "status": "ok",
        "board": "tang-nano-9k",
        "top": "blinky",
        "bitstream_url": f"/api/runs/{run_id}/files/build/bitstream.fs",
        "timing_met": True,
        **overrides,
    }


ROUTES: dict[str, Any] = {
    "/api/boards": [TANG],
    # Newest first: a running build, a lint run, a failed build, then the one to use.
    "/api/projects/3/runs?limit=200": [
        {"id": "r4", "kind": "fpga", "status": "running"},
        {"id": "r3", "kind": "lint", "status": "succeeded"},
        {"id": "r2", "kind": "fpga", "status": "succeeded"},
        {"id": "r1", "kind": "fpga", "status": "succeeded"},
    ],
    "/api/projects/3/runs/r2": {"fpga": {**build("r2"), "status": "failed", "bitstream_url": None}},
    "/api/projects/3/runs/r1": {"fpga": build("r1")},
    "/api/projects/4/runs?limit=200": [{"id": "r9", "kind": "sim", "status": "succeeded"}],
    "/api/runs/r1": {"kind": "fpga", "status": "succeeded", "result": build("r1")},
    "/api/runs/r5": {
        "kind": "fpga",
        "status": "succeeded",
        "result": build("r5", timing_met=False),
    },
    "/api/runs/r9": {"kind": "sim", "status": "succeeded", "result": {}},
    "/api/runs/r1/files/build/bitstream.fs": BITSTREAM,
    "/api/runs/r5/files/build/bitstream.fs": BITSTREAM,
}


class Stub(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        body = ROUTES.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture(scope="module")
def api() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture
def flashed(monkeypatch: pytest.MonkeyPatch) -> list[tuple[list[str], bytes]]:
    """Commands that would have run, with the bitstream they were given."""
    calls: list[tuple[list[str], bytes]] = []

    def fake_run(command: list[str]) -> Any:
        calls.append((command, Path(command[-1]).read_bytes()))
        return type("Done", (), {"returncode": 0})()

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    monkeypatch.setattr(tool.shutil, "which", lambda name: f"/usr/bin/{name}")
    return calls


def test_latest_build_of_a_project_goes_to_sram(
    api: str, flashed: list[tuple[list[str], bytes]], capsys: pytest.CaptureFixture[str]
) -> None:
    assert tool.main(["--api", api, "--project", "3"]) == 0

    [(command, data)] = flashed
    assert command[:3] == ["openFPGALoader", "-b", "tangnano9k"]
    assert "-f" not in command  # SRAM unless --flash
    assert Path(command[-1]).name == "blinky-tang-nano-9k.fs"
    assert data == BITSTREAM
    out = capsys.readouterr().out
    assert "Bitstream run r1" in out and "Ke SRAM board" in out


def test_flash_and_extra_arguments(api: str, flashed: list[tuple[list[str], bytes]]) -> None:
    assert tool.main(["--api", api, "--run", "r1", "--flash", "--", "--verbose"]) == 0

    [(command, _)] = flashed
    assert command[:5] == ["openFPGALoader", "-b", "tangnano9k", "-f", "--verbose"]


def test_local_file_needs_a_board(
    api: str,
    flashed: list[tuple[list[str], bytes]],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    local = tmp_path / "mine.fs"
    local.write_bytes(b"local")

    assert tool.main(["--api", api, "--file", str(local), "--board", "tang-nano-9k"]) == 0
    assert flashed == [(["openFPGALoader", "-b", "tangnano9k", str(local)], b"local")]

    with pytest.raises(SystemExit):
        tool.main(["--api", api, "--file", str(local)])
    assert "--file perlu --board" in capsys.readouterr().err


def test_dry_run_only_prints(
    api: str, flashed: list[tuple[list[str], bytes]], capsys: pytest.CaptureFixture[str]
) -> None:
    assert tool.main(["--api", api, "--run", "r5", "--dry-run"]) == 0

    assert flashed == []
    out = capsys.readouterr().out
    assert "Perintah: openFPGALoader -b tangnano9k" in out
    assert "tidak mencapai target clock" in out  # r5 missed timing


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--project", "4"], "belum punya build FPGA"),
        (["--project", "99"], "Proyek 99 tidak ditemukan."),
        (["--run", "r9"], "bukan build FPGA"),
        (["--run", "nope"], "Tidak ditemukan"),
        (["--file", "tidak-ada.fs", "--board", "tang-nano-9k"], "File bitstream tidak ada"),
        (["--run", "r1", "--board", "x"], ""),  # --board is only read with --file
    ],
)
def test_problems_are_explained(
    api: str,
    flashed: list[tuple[list[str], bytes]],
    capsys: pytest.CaptureFixture[str],
    args: list[str],
    message: str,
) -> None:
    code = tool.main(["--api", api, *args])

    if message:
        assert code == 2
        assert message in capsys.readouterr().err
        assert flashed == []
    else:
        assert code == 0


def test_missing_openfpgaloader_points_at_the_readme(
    api: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(tool.shutil, "which", lambda name: None)

    assert tool.main(["--api", api, "--run", "r1"]) == 2
    assert "tools/flash/README.md" in capsys.readouterr().err


def test_unreachable_backend(capsys: pytest.CaptureFixture[str]) -> None:
    assert tool.main(["--api", "http://127.0.0.1:9", "--project", "3"]) == 2
    assert "tidak bisa dihubungi" in capsys.readouterr().err


def test_unknown_board(api: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    local = tmp_path / "x.bin"
    local.write_bytes(b"x")
    assert tool.main(["--api", api, "--file", str(local), "--board", "papan-x"]) == 2
    assert "Board 'papan-x' tidak dikenal" in capsys.readouterr().err
