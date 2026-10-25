"""Shared test helpers."""

import time
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient

TERMINAL = {"succeeded", "failed", "cancelled", "timeout"}


def write_exercise(root: Path, ex_id: str, **overrides: Any) -> Path:
    """Create a minimal valid exercise folder; overrides replace exercise.yaml fields."""
    d = root / ex_id
    d.mkdir(parents=True, exist_ok=True)
    meta: dict[str, Any] = {
        "id": ex_id,
        "title": f"Soal {ex_id}",
        "step": 1,
        "level": 1,
        "topics": ["sequential"],
        "toplevel": "top",
        "language": "verilog",
        "files": {
            "starter": "starter.v",
            "solution": "solution.v",
            "test": "test_top.py",
            "statement": "README.md",
        },
        "timeout_s": 30,
        "hints": ["petunjuk 1", "petunjuk 2"],
    }
    meta.update(overrides)
    meta = {k: v for k, v in meta.items() if v is not None}
    (d / "exercise.yaml").write_text(yaml.safe_dump(meta, allow_unicode=True), encoding="utf-8")
    for name in ("starter.v", "solution.v", "test_top.py", "README.md"):
        (d / name).write_text(f"// {name}\n", encoding="utf-8")
    return d


def wait_for_status(
    client: TestClient, run_id: str, statuses: set[str], timeout: float = 3.0
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] in statuses:
            return run
        assert time.monotonic() < deadline, f"run stuck in {run['status']}"
        time.sleep(0.02)
