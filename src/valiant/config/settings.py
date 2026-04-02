"""Application settings loaded from environment variables / .env file."""
from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VALIANT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────
    database_url: str = "sqlite:///./valiant.db"

    # ── API Auth ──────────────────────────────────────────
    # Comma-separated list of valid API keys. Empty = auth disabled (dev only).
    api_keys_raw: str = ""

    @field_validator("api_keys_raw", mode="before")
    @classmethod
    def _coerce_none(cls, v: object) -> str:
        return v if isinstance(v, str) else ""

    @property
    def api_keys(self) -> list[str]:
        return [k.strip() for k in self.api_keys_raw.split(",") if k.strip()]

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_keys)

    # ── CORS ──────────────────────────────────────────────
    allowed_origins_raw: str = "http://localhost:8501,http://localhost:3000"

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins_raw.split(",") if o.strip()]

    # ── Ports ─────────────────────────────────────────────
    api_port: int = 8000
    ui_port: int = 8501

    # ── Logging ───────────────────────────────────────────
    log_level: str = "INFO"
    log_format: str = "console"  # "console" | "json"

    # ── Execution ─────────────────────────────────────────
    default_timeout: float = 120.0
    max_parallel_steps: int = 10

    # ── Workflow discovery ────────────────────────────────
    workflow_dirs: str = ""

    @property
    def extra_workflow_dirs(self) -> list[str]:
        return [d.strip() for d in self.workflow_dirs.split(":") if d.strip()]


# Module-level singleton — import this everywhere
settings = Settings()
