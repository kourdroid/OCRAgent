from __future__ import annotations

import io
import uuid
from typing import Any

import aiofiles
import httpx
from pypdf import PdfReader, PdfWriter

from src.dossiers.models import DecisionStatus, DocumentSegment, DocumentType
from src.dossiers.rules import evaluate_ruleset
from src.infrastructure.dossier_repos import DossierNotFoundError, DossierRepository
from src.plugins.registry import WorkflowPluginRegistry
from src.providers.base import DocumentIntelligenceProvider, TerminalProviderError


def count_pdf_pages(pdf_bytes: bytes) -> int:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    page_count = len(reader.pages)
    if page_count < 1:
        raise ValueError("PDF contains no pages")
    return page_count


def extract_page_range(pdf_bytes: bytes, *, page_start: int, page_end: int) -> bytes:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page_index in range(page_start - 1, page_end):
        writer.add_page(reader.pages[page_index])
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def normalize_segments(
    segments: list[DocumentSegment],
    *,
    page_count: int,
    confidence_threshold: float = 0.75,
) -> list[DocumentSegment]:
    ordered = sorted(segments, key=lambda item: (item.page_start, item.page_end))
    expected_page = 1
    normalized: list[DocumentSegment] = []

    for segment in ordered:
        if (
            segment.page_start != expected_page
            or segment.page_end > page_count
            or segment.page_start > segment.page_end
        ):
            return [
                DocumentSegment(
                    page_start=1,
                    page_end=page_count,
                    document_type=DocumentType.UNKNOWN,
                    confidence=0.0,
                )
            ]
        normalized.append(
            segment.model_copy(
                update={
                    "document_type": (
                        segment.document_type
                        if segment.confidence >= confidence_threshold
                        else DocumentType.UNKNOWN
                    )
                }
            )
        )
        expected_page = segment.page_end + 1

    if expected_page != page_count + 1:
        return [
            DocumentSegment(
                page_start=1,
                page_end=page_count,
                document_type=DocumentType.UNKNOWN,
                confidence=0.0,
            )
        ]
    return normalized


async def load_pdf_bytes(file_path: str) -> bytes:
    if file_path.startswith(("http://", "https://")):
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(file_path)
            response.raise_for_status()
            return response.content
    async with aiofiles.open(file_path, "rb") as file:
        return await file.read()


class DossierProcessor:
    def __init__(
        self,
        *,
        repository: DossierRepository,
        provider: DocumentIntelligenceProvider,
        workflow_registry: WorkflowPluginRegistry,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._workflow_registry = workflow_registry

    async def process_source(
        self,
        *,
        job_id: str,
        case_id: str,
        client_id: str,
        workflow_id: str,
        file_path: str,
    ) -> None:
        source = await self._repository.get_source_for_job(
            job_id=job_id,
            client_id=client_id,
        )
        if not source:
            raise DossierNotFoundError(job_id)
        if source["job_status"] in {"COMPLETED", "FAILED"}:
            return
        if str(source["case_id"]) != case_id:
            raise TerminalProviderError("Queue case_id does not match the stored job")
        if source["workflow_id"] != workflow_id:
            raise TerminalProviderError("Queue workflow_id does not match the stored job")

        workflow = self._workflow_registry.get(workflow_id)
        await self._repository.mark_source_processing(job_id=job_id, client_id=client_id)

        pdf_bytes = await load_pdf_bytes(file_path)
        page_count = count_pdf_pages(pdf_bytes)
        classification = await self._provider.classify_pdf(
            pdf_bytes,
            page_count=page_count,
            supported_types=workflow.supported_document_types,
        )
        segments = normalize_segments(classification.segments, page_count=page_count)

        persisted_segments: list[dict[str, Any]] = []
        for segment in segments:
            if segment.page_start == 1 and segment.page_end == page_count:
                segment_pdf = pdf_bytes
            else:
                segment_pdf = extract_page_range(
                    pdf_bytes,
                    page_start=segment.page_start,
                    page_end=segment.page_end,
                )
            allowed_fields = workflow.schema_for(segment.document_type)
            facts: list[dict[str, Any]] = []
            if segment.document_type is not DocumentType.UNKNOWN:
                extraction = await self._provider.extract_pdf(
                    segment_pdf,
                    document_type=segment.document_type,
                    allowed_fields=allowed_fields,
                )
                for fact in extraction.facts:
                    source_page = segment.page_start + fact.page - 1
                    if source_page > segment.page_end:
                        raise TerminalProviderError(
                            f"Evidence page {fact.page} is outside the classified segment"
                        )
                    facts.append(
                        fact.model_copy(update={"page": source_page}).model_dump(mode="json")
                    )

            persisted_segments.append(
                {
                    "document_id": str(uuid.uuid4()),
                    "page_start": segment.page_start,
                    "page_end": segment.page_end,
                    "document_type": segment.document_type.value,
                    "classification_confidence": segment.confidence,
                    "schema_version": (
                        f"{workflow.workflow_id}:{workflow.workflow_version}:"
                        f"{segment.document_type.value}"
                    ),
                    "facts": facts,
                }
            )

        persisted_case_id = await self._repository.save_source_results(
            job_id=job_id,
            client_id=client_id,
            provider_id=self._provider.provider_id,
            model_id=self._provider.model_id,
            segments=persisted_segments,
        )
        if persisted_case_id != case_id:
            raise TerminalProviderError("Processed source was persisted to the wrong case")

        if not await self._repository.is_case_ready_for_decision(
            case_id=case_id,
            client_id=client_id,
        ):
            return

        case_context = await self._repository.load_case_context(
            case_id=case_id,
            client_id=client_id,
        )
        active_ruleset = await self._repository.get_active_ruleset(
            client_id=client_id,
            workflow_id=workflow_id,
        )
        if active_ruleset:
            decision = evaluate_ruleset(case_context, active_ruleset)
        else:
            # A draft is useful for review but is never an authority for automatic clearance.
            decision = workflow.reconcile(case_context).model_copy(
                update={
                    "status": DecisionStatus.REVIEW_REQUIRED,
                    "ruleset_id": "UNCONFIRMED",
                    "ruleset_version": "0",
                    "summary": "No confirmed ruleset is active; human review is required.",
                }
            )
        report = workflow.build_report(case_context, decision)
        await self._repository.save_decision(
            case_context=case_context,
            decision=decision,
            report_payload=report,
        )
