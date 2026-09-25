from __future__ import annotations

from src.config import Settings
from src.infrastructure.openai_provider import OpenAICompatibleDocumentProvider
from src.infrastructure.paddle_document_provider import PaddleDocumentIntelligenceProvider
from src.infrastructure.paddle_ocr_client import PaddleOCRClient
from src.providers.base import DocumentIntelligenceProvider


def build_document_provider(settings: Settings) -> DocumentIntelligenceProvider:
    if settings.document_provider == "paddle":
        ocr = PaddleOCRClient(
            base_url=settings.paddle_ocr_url,
            model_id=settings.paddle_ocr_model,
            timeout_s=settings.paddle_ocr_timeout_s,
        )
        return PaddleDocumentIntelligenceProvider(ocr)
    if settings.document_provider == "openai":
        return OpenAICompatibleDocumentProvider(settings)
    raise ValueError(f"Unsupported DOCUMENT_PROVIDER: {settings.document_provider}")
