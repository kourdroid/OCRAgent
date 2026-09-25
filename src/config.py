"""
Configuration loader for Ironclad-OCR.
Centralizes all environment and path configurations.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.logging_setup import setup_logging


class Settings(BaseModel):
    document_provider: Literal["paddle", "openai"] = "paddle"
    paddle_ocr_url: str = "http://localhost:8080"
    paddle_ocr_model: str = "PP-OCRv6_small_det+PP-OCRv6_small_rec"
    paddle_ocr_timeout_s: float = Field(default=300.0, gt=0.0, le=1200.0)

    llm_api_key: str = Field(default="")
    llm_api_key_required: bool = Field(default=True)
    llm_base_url: str | None = Field(default=None)
    model_name: str = Field(default="gpt-4o")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    drift_threshold: float = Field(default=0.8, ge=0.0, le=1.0)

    database_url: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_publishable_key: str | None = None
    super_admin_email: str | None = None

    redis_url: str = Field(default="redis://localhost:6379/0")
    webhook_url: str | None = None
    storage_upload_timeout_s: float = Field(default=60.0, gt=0.0, le=300.0)
    max_upload_mb: int = Field(default=25, ge=1, le=250)
    max_dossier_files: int = Field(default=20, ge=1, le=100)
    max_dossier_pages: int = Field(default=200, ge=1, le=2000)

    data_dir: str = Field(default="./data")
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
            document_provider=os.getenv("DOCUMENT_PROVIDER", "paddle").lower(),
            paddle_ocr_url=os.getenv("PADDLE_OCR_URL", "http://localhost:8080"),
            paddle_ocr_model=os.getenv(
                "PADDLE_OCR_MODEL",
                "PP-OCRv6_small_det+PP-OCRv6_small_rec",
            ),
            paddle_ocr_timeout_s=float(os.getenv("PADDLE_OCR_TIMEOUT_S", "300.0")),
            llm_api_key=os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))),
            llm_api_key_required=os.getenv("LLM_API_KEY_REQUIRED", "true").lower()
            in {"1", "true", "yes", "on"},
            llm_base_url=os.getenv("LLM_BASE_URL", os.getenv("OPENAI_BASE_URL")),
            model_name=os.getenv("MODEL_NAME", "gpt-4o"),
            temperature=float(os.getenv("TEMPERATURE", "0.1")),
            drift_threshold=float(os.getenv("DRIFT_THRESHOLD", "0.8")),
            database_url=os.getenv("DATABASE_URL"),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
            supabase_publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY", os.getenv("SUPABASE_ANON_KEY")),
            super_admin_email=os.getenv("SUPER_ADMIN_EMAIL"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            webhook_url=os.getenv("WEBHOOK_URL"),
            storage_upload_timeout_s=float(os.getenv("STORAGE_UPLOAD_TIMEOUT_S", "60.0")),
            max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "25")),
            max_dossier_files=int(os.getenv("MAX_DOSSIER_FILES", "20")),
            max_dossier_pages=int(os.getenv("MAX_DOSSIER_PAGES", "200")),
            data_dir=os.getenv("DATA_DIR", "./data"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings.from_env()

    setup_logging(level=settings.log_level)

    try:
        settings.data_path.mkdir(parents=True, exist_ok=True)
        settings.uploads_dir.mkdir(parents=True, exist_ok=True)
        settings.output_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    return settings
