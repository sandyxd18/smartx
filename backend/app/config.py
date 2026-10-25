"""Application settings, read from environment variables and the repo-level .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_by_name=True,
    )

    data_dir: Path = Field(default=Path("data"), validation_alias="SMARTX_DATA_DIR")
    bind: str = Field(default="127.0.0.1", validation_alias="SMARTX_BIND")
    port: int = Field(default=8080, validation_alias="SMARTX_PORT")

    toolchain_image: str = Field(
        default="smartx/toolchain:local", validation_alias="TOOLCHAIN_IMAGE"
    )
    asic_image: str = Field(default="", validation_alias="ASIC_IMAGE")
    oss_cad_suite_date: str = Field(default="", validation_alias="OSS_CAD_SUITE_DATE")

    job_light_concurrency: int = Field(default=2, validation_alias="JOB_LIGHT_CONCURRENCY")
    job_heavy_concurrency: int = Field(default=1, validation_alias="JOB_HEAVY_CONCURRENCY")
    job_light_timeout_s: int = Field(default=120, validation_alias="JOB_LIGHT_TIMEOUT_S")
    job_heavy_timeout_s: int = Field(default=7200, validation_alias="JOB_HEAVY_TIMEOUT_S")
    job_light_memory: str = Field(default="4g", validation_alias="JOB_LIGHT_MEMORY")
    job_heavy_memory: str = Field(default="12g", validation_alias="JOB_HEAVY_MEMORY")

    @field_validator("data_dir")
    @classmethod
    def _resolve_data_dir(cls, value: Path) -> Path:
        # Relative paths in .env are relative to the repo root, not the cwd.
        return value if value.is_absolute() else (REPO_ROOT / value).resolve()

    @property
    def db_path(self) -> Path:
        return self.data_dir / "smartx.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
