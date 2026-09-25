from __future__ import annotations

import pytest

from src.dossiers.processor import DossierProcessor


class _Repository:
    async def get_source_for_job(self, **_kwargs):
        return {
            "job_status": "FAILED",
            "case_id": "case-1",
            "workflow_id": "morocco_import_dossier",
        }

    async def mark_source_processing(self, **_kwargs) -> None:
        raise AssertionError("terminal jobs must not return to PROCESSING")


class _Provider:
    provider_id = "test"
    model_id = "test"

    async def classify_pdf(self, *_args, **_kwargs):
        raise AssertionError("terminal jobs must not call the provider")


class _Workflows:
    def get(self, _workflow_id: str):
        raise AssertionError("terminal jobs must not load a workflow")


@pytest.mark.asyncio
async def test_failed_job_is_acknowledgeable_without_reprocessing() -> None:
    processor = DossierProcessor(
        repository=_Repository(),  # type: ignore[arg-type]
        provider=_Provider(),  # type: ignore[arg-type]
        workflow_registry=_Workflows(),  # type: ignore[arg-type]
    )

    await processor.process_source(
        job_id="job-1",
        case_id="case-1",
        client_id="delassus",
        workflow_id="morocco_import_dossier",
        file_path="https://storage/document.pdf",
    )
