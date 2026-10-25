"""Runtime configuration, read from environment variables prefixed with ``CANECA_``."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION = "0.1.0"


def default_data_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "CanecaQuest"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "CanecaQuest"
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "caneca-quest"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CANECA_", env_file=".env", extra="ignore")

    data_dir: Path = Field(default_factory=default_data_dir)
    host: str = "127.0.0.1"
    port: int = 8765
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "tauri://localhost",
        "http://tauri.localhost",
    ]
    # When set, every /api request must carry "Authorization: Bearer <token>".
    # The desktop shell generates one per launch so other local programs can't drive the API.
    api_token: str | None = None
    static_dir: Path | None = None
    ollama_url: str = "http://127.0.0.1:11434"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str | None = None
    max_body_bytes: int = 256 * 1024
    max_import_bytes: int = 8 * 1024 * 1024
    rate_limit_per_minute: int = 90
    backups_to_keep: int = 5
    log_level: str = "info"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "caneca.db"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def secrets_path(self) -> Path:
        return self.data_dir / "secrets.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
