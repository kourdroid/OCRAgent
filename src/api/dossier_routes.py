from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import uuid
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from pypdf import PdfReader

from src.config import get_settings
from src.api.auth import require_super_admin
from src.dossiers.models import (
    CaseStatus,
    DossierReprocessRequest,
    DossierReviewRequest,
    IntakeChannel,
)
from src.dossiers.reporting import build_canonical_report, render_report_pdf
from src.infrastructure.dossier_repos import (
    DecisionVersionConflictError,
    DossierNotFoundError,
    DossierRepository,
    InvalidReviewResolutionError,
)
from src.infrastructure.supabase_storage import SupabaseStorage
from src.plugins.registry import (
    UnknownClientPluginError,
    get_client_config,
    get_workflow_plugin,
    normalize_client_id,
)

router = APIRouter(
    prefix="/dossiers",
    tags=["dossiers"],
    dependencies=[Depends(require_super_admin)],
)
logger = logging.getLogger(__name__)


class DossierIngestResponse(BaseModel):
    case_id: str
    document_ids: list[str]
    job_ids: list[str]
    status: str


class DossierReprocessResponse(BaseModel):
    case_id: str
    job_ids: list[str]
    status: str


def _require_dossier_client(client_id: str | None) -> tuple[str, Any, Any]:
    normalized = normalize_client_id(client_id or "delassus")
    try:
        config = get_client_config(normalized)
        workflow = get_workflow_plugin(config.workflow_id)
    except UnknownClientPluginError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown client_id: {exc.client_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return normalized, config, workflow


def _require_database_url() -> str:
    database_url = get_settings().database_url
    if not database_url:
        raise HTTPException(status_code=500, detail="Database URL not configured")
    return database_url


def _require_case_id(case_id: str) -> None:
    try:
        uuid.UUID(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Dossier not found") from exc


async def _reprocess_with_deadlock_retry(
    repository: DossierRepository,
    *,
    case_id: str,
    client_id: str,
    document_ids: list[str],
    reason: str,
) -> list[str]:
    for attempt in range(3):
        try:
            return await repository.reprocess_sources(
                case_id=case_id,
                client_id=client_id,
                document_ids=document_ids,
                reason=reason,
            )
        except asyncpg.DeadlockDetectedError as exc:
            if attempt == 2:
                raise HTTPException(
                    status_code=503,
                    detail="Dossier is busy; retry reprocessing",
                ) from exc
            await asyncio.sleep(0.1 * (2**attempt))
    raise RuntimeError("unreachable")


@router.post("", response_model=DossierIngestResponse)
async def ingest_dossier(
    files: list[UploadFile] = File(...),
    client_id: str = Form(default="delassus"),
    external_reference: str | None = Form(default=None),
    intake_channel: IntakeChannel = Form(default=IntakeChannel.WEB_UPLOAD),
    sender_party_id: str | None = Form(default=None),
    channel_reference: str | None = Form(default=None),
    idempotency_key: str | None = Form(default=None),
    issuer_manifest_json: str | None = Form(default=None),
) -> DossierIngestResponse:
    settings = get_settings()
    normalized_client_id, config, workflow = _require_dossier_client(client_id)
    database_url = _require_database_url()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status_code=500, detail="Supabase Storage not configured")
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF is required")
    if len(files) > settings.max_dossier_files:
        raise HTTPException(
            status_code=413,
            detail=f"A dossier can contain at most {settings.max_dossier_files} files",
        )

    issuer_manifest: dict[str, str | None] = {}
    if issuer_manifest_json:
        try:
            candidate = json.loads(issuer_manifest_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="issuer_manifest_json must be a JSON object") from exc
        if not isinstance(candidate, dict) or not all(
            isinstance(key, str) and (value is None or isinstance(value, str))
            for key, value in candidate.items()
        ):
            raise HTTPException(status_code=422, detail="issuer_manifest_json must map filenames to party IDs")
        issuer_manifest = candidate

    repository = DossierRepository(database_url)
    known_parties = {
        item["party_id"] for item in await repository.list_parties(client_id=normalized_client_id)
    }
    requested_party_ids = {party_id for party_id in issuer_manifest.values() if party_id}
    if sender_party_id:
        requested_party_ids.add(sender_party_id)
    if not requested_party_ids.issubset(known_parties):
        raise HTTPException(status_code=404, detail="Sender or issuer party was not found for this client")

    case_id = str(uuid.uuid4())
    storage = SupabaseStorage(
        settings.supabase_url,
        settings.supabase_service_role_key,
        timeout_s=settings.storage_upload_timeout_s,
    )
    uploaded_paths: list[str] = []
    sources: list[dict[str, Any]] = []
    total_pages = 0
    max_bytes = settings.max_upload_mb * 1024 * 1024

    try:
        for upload in files:
            filename = upload.filename or "document.pdf"
            if not filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail=f"{filename}: only PDF files are supported")
            content = await upload.read()
            if not content:
                raise HTTPException(status_code=400, detail=f"{filename}: file is empty")
            if len(content) > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"{filename}: file exceeds {settings.max_upload_mb} MB",
                )
            if not content.startswith(b"%PDF"):
                raise HTTPException(status_code=400, detail=f"{filename}: invalid PDF signature")
            try:
                page_count = len(PdfReader(io.BytesIO(content)).pages)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"{filename}: invalid PDF") from exc
            if page_count < 1:
                raise HTTPException(status_code=400, detail=f"{filename}: PDF has no pages")
            total_pages += page_count
            if total_pages > settings.max_dossier_pages:
                raise HTTPException(
                    status_code=413,
                    detail=f"Dossier exceeds {settings.max_dossier_pages} pages",
                )

            document_id = str(uuid.uuid4())
            job_id = str(uuid.uuid4())
            storage_path = (
                f"dossiers/{normalized_client_id}/{case_id}/{document_id}.pdf"
            )
            file_url = await storage.upload(storage_path, content)
            uploaded_paths.append(storage_path)
            sources.append(
                {
                    "document_id": document_id,
                    "job_id": job_id,
                    "original_filename": filename,
                    "storage_path": storage_path,
                    "file_url": file_url,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "page_count": page_count,
                    "idempotency_key": f"job:{job_id}:attempt:0",
                    "issuer_party_id": issuer_manifest.get(filename),
                    "provenance_status": (
                        "COMPLETE" if sender_party_id and issuer_manifest.get(filename)
                        else "MISSING_SENDER" if issuer_manifest.get(filename)
                        else "MISSING_ISSUER" if sender_party_id
                        else "MISSING_BOTH"
                    ),
                }
            )

        result = await repository.create_case_with_sources(
            case_id=case_id,
            client_id=normalized_client_id,
            external_reference=(external_reference or "").strip() or None,
            workflow_id=config.workflow_id,
            workflow_version=workflow.workflow_version,
            sources=sources,
            intake={
                "intake_channel": intake_channel.value,
                "sender_party_id": sender_party_id,
                "channel_reference": (channel_reference or "").strip() or None,
                "idempotency_key": (idempotency_key or "").strip() or None,
                "metadata": {"adapter": "fastapi_dossiers"},
            },
        )
        return DossierIngestResponse.model_validate(result)
    except HTTPException:
        if uploaded_paths:
            try:
                await storage.delete(uploaded_paths)
            except Exception:
                logger.exception("step=dossier_cleanup status=failed case_id=%s", case_id)
        raise
    except asyncpg.PostgresError as exc:
        if uploaded_paths:
            try:
                await storage.delete(uploaded_paths)
            except Exception:
                logger.exception("step=dossier_cleanup status=failed case_id=%s", case_id)
        logger.exception("step=dossier_ingest status=database_failed case_id=%s", case_id)
        raise HTTPException(status_code=502, detail="Database operation failed") from exc
    except Exception as exc:
        if uploaded_paths:
            try:
                await storage.delete(uploaded_paths)
            except Exception:
                logger.exception("step=dossier_cleanup status=failed case_id=%s", case_id)
        logger.exception("step=dossier_ingest status=failed case_id=%s", case_id)
        raise HTTPException(status_code=500, detail="Dossier ingestion failed") from exc


@router.get("")
async def list_dossiers(
    client_id: str = Query(default="delassus"),
    status: CaseStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    normalized_client_id, _, _ = _require_dossier_client(client_id)
    repository = DossierRepository(_require_database_url())
    return await repository.list_cases(
        client_id=normalized_client_id,
        status=status.value if status else None,
        limit=limit,
        offset=offset,
    )


@router.get("/{case_id}")
async def get_dossier(
    case_id: str,
    client_id: str = Query(default="delassus"),
) -> dict[str, Any]:
    normalized_client_id, _, _ = _require_dossier_client(client_id)
    _require_case_id(case_id)
    repository = DossierRepository(_require_database_url())
    case = await repository.get_case(case_id=case_id, client_id=normalized_client_id)
    if not case:
        raise HTTPException(status_code=404, detail="Dossier not found")
    return case


@router.post("/{case_id}/reviews")
async def review_dossier(
    case_id: str,
    payload: DossierReviewRequest,
) -> dict[str, Any]:
    normalized_client_id, _, _ = _require_dossier_client(payload.client_id)
    _require_case_id(case_id)
    repository = DossierRepository(_require_database_url())
    try:
        review = await repository.resolve_review(
            case_id=case_id,
            client_id=normalized_client_id,
            action=payload.action,
            comment=payload.comment,
            expected_decision_version=payload.expected_decision_version,
            idempotency_key=payload.idempotency_key,
        )
    except DossierNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dossier or decision not found") from exc
    except DecisionVersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidReviewResolutionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"case_id": case_id, "status": "RESOLVED", "review": review}


@router.post("/{case_id}/reprocess", response_model=DossierReprocessResponse)
async def reprocess_dossier(
    case_id: str,
    payload: DossierReprocessRequest,
) -> DossierReprocessResponse:
    normalized_client_id, _, _ = _require_dossier_client(payload.client_id)
    _require_case_id(case_id)
    repository = DossierRepository(_require_database_url())
    try:
        job_ids = await _reprocess_with_deadlock_retry(
            repository,
            case_id=case_id,
            client_id=normalized_client_id,
            document_ids=payload.document_ids,
            reason=payload.reason,
        )
    except (DossierNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Dossier or document not found") from exc
    return DossierReprocessResponse(
        case_id=case_id,
        job_ids=job_ids,
        status="PROCESSING",
    )


@router.get("/{case_id}/report")
async def get_dossier_report(
    case_id: str,
    client_id: str = Query(default="delassus"),
    format: str = Query(default="json", pattern="^(json|pdf)$"),
) -> Any:
    normalized_client_id, _, _ = _require_dossier_client(client_id)
    _require_case_id(case_id)
    repository = DossierRepository(_require_database_url())
    case = await repository.get_case(case_id=case_id, client_id=normalized_client_id)
    if not case:
        raise HTTPException(status_code=404, detail="Dossier not found")
    try:
        report = build_canonical_report(case)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if format == "json":
        return report.model_dump(mode="json")

    content = render_report_pdf(report)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="ironclad-{case_id}.pdf"'
        },
    )
