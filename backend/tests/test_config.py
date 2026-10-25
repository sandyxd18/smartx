from pathlib import Path

import pytest

from app.config import REPO_ROOT, Settings


def test_defaults_bind_to_localhost() -> None:
    s = Settings(_env_file=None)
    assert s.bind == "127.0.0.1"
    assert s.port == 8080
    assert s.toolchain_image == "smartx/toolchain:local"
    assert s.job_light_concurrency == 2
    assert s.job_heavy_concurrency == 1


def test_relative_data_dir_is_resolved_against_repo_root() -> None:
    s = Settings(_env_file=None, data_dir=Path("data"))
    assert s.data_dir == REPO_ROOT / "data"
    assert s.db_path == REPO_ROOT / "data" / "smartx.db"


def test_absolute_data_dir_is_kept(tmp_path: Path) -> None:
    s = Settings(_env_file=None, data_dir=tmp_path)
    assert s.data_dir == tmp_path


def test_reads_environment_variables(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SMARTX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SMARTX_PORT", "9090")
    monkeypatch.setenv("JOB_LIGHT_CONCURRENCY", "4")
    monkeypatch.setenv("JOB_LIGHT_TIMEOUT_S", "30")
    s = Settings(_env_file=None)
    assert s.data_dir == tmp_path
    assert s.port == 9090
    assert s.job_light_concurrency == 4
    assert s.job_light_timeout_s == 30


def test_reads_env_file(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("SMARTX_BIND=0.0.0.0\nOSS_CAD_SUITE_DATE=2026-10-24\nUNRELATED=1\n")
    s = Settings(_env_file=env)
    assert s.bind == "0.0.0.0"
    assert s.oss_cad_suite_date == "2026-10-24"
