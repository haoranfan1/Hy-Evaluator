"""Typed application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings; secrets are never included in public health output."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    hy3_base_url: AnyHttpUrl | None = None
    hy3_model: str | None = None
    hy3_api_key: SecretStr | None = None
    hy3_reasoning_effort: str = "high"
    hy3_temperature: float = Field(default=0.9, ge=0.0, le=2.0)
    hy3_top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    hy3_timeout_seconds: float = Field(default=90.0, gt=0.0, le=300.0)
    semantic_context_limit_chars: int = Field(default=180_000, ge=1_000)

    workbench_data_dir: Path = Path(".local/workbench")
    harbor_jobs_dir: Path = Path(".local/harbor/jobs")
    results_dir: Path = Path("results")
    slices_dir: Path = Path("data/evaluation-slices")
    workbench_host: str = "127.0.0.1"
    workbench_port: int = Field(default=8000, ge=1, le=65535)

    @property
    def hy3_configured(self) -> bool:
        """Whether all values required for an explicit Hy3 request are present."""

        return bool(self.hy3_base_url and self.hy3_model and self.hy3_api_key)


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process."""

    return Settings()
