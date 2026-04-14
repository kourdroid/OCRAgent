"""
Configuration loader for Ironclad-OCR.
Centralizes all environment and path configurations.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.logging_setup import setup_logging


class Settings(BaseModel):
    google_api_key: str = Field(min_length=1)
    model_name: str = Field(default="gemini-3-flash-preview")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    drift_threshold: float = Field(default=0.8, ge=0.0, le=1.0)

    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    redis_url: str = Field(default="redis://localhost:6379/0")
    webhook_url: str | None = None

    data_dir: str = Field(default="./data")
    poppler_bin: str | None = None
    log_level: str = Field(default="INFO")

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def data_path(self) -> Path:
        return (self.base_dir / self.data_dir).resolve()

    @property
    def uploads_dir(self) -> Path:
        return self.data_path / "uploads"

    @property
    def output_dir(self) -> Path:
        return self.data_path / "output"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
            model_name=os.getenv("MODEL_NAME", "gemini-3-flash-preview"),
            temperature=float(os.getenv("TEMPERATURE", "0.1")),
            drift_threshold=float(os.getenv("DRIFT_THRESHOLD", "0.8")),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            webhook_url=os.getenv("WEBHOOK_URL"),
            data_dir=os.getenv("DATA_DIR", "./data"),
            poppler_bin=os.getenv("POPPLER_BIN"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings.from_env()

    setup_logging(level=settings.log_level)

    settings.data_path.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)

    if settings.poppler_bin and os.name == "nt" and os.path.exists(settings.poppler_bin):
        current_path = os.environ.get("PATH", "")
        if settings.poppler_bin.lower() not in current_path.lower():
            os.environ["PATH"] = current_path + os.pathsep + settings.poppler_bin

    return settings
