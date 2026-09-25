from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.dossiers.models import DocumentClassification, DocumentExtraction, DocumentType


class ProviderError(RuntimeError):
    """Base error raised by a document intelligence provider."""


class RetryableProviderError(ProviderError):
    """A transient provider failure that can be retried."""


class TerminalProviderError(ProviderError):
    """A provider or request failure that must not be retried."""


@dataclass(frozen=True)
class ProviderCapabilities:
    pdf_input: bool
    image_input: bool
    structured_output: bool
    bounding_boxes: bool


class DocumentIntelligenceProvider(Protocol):
    provider_id: str
    model_id: str
    capabilities: ProviderCapabilities

    async def healthcheck(self) -> dict[str, str | bool]: ...

    async def classify_pdf(
        self,
        pdf_bytes: bytes,
        *,
        page_count: int,
        supported_types: frozenset[DocumentType],
    ) -> DocumentClassification: ...

    async def extract_pdf(
        self,
        pdf_bytes: bytes,
        *,
        document_type: DocumentType,
        allowed_fields: tuple[str, ...],
    ) -> DocumentExtraction: ...
