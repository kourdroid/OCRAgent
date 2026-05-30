from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Optional

import aiofiles
import asyncpg
import tempfile
import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.config import get_settings
from src.core.pdf_splitter import split_pdf
from src.infrastructure.redis_queue import RedisQueue
from src.infrastructure.supabase_repos import SupabaseJobsRepository, SupabaseRegistryRepository, get_connection_pool
from src.infrastructure.supabase_storage import SupabaseStorage

router = APIRouter()
logger = logging.getLogger(__name__)


class SplitEnqueueError(RuntimeError):
    def __init__(self, *, phase: str, split_file: str, original_error: Exception) -> None:
        self.phase = phase
        self.split_file = split_file
        self.original_error = original_error
        super().__init__(f"{phase} failed for {split_file}: {original_error}")


def _raise_if_missing_supabase_tables(exc: asyncpg.PostgresError) -> None:
    code = getattr(exc, "sqlstate", "")
    if code != "42P01":  # undefined_table
        return
    raise HTTPException(
        status_code=503,
        detail="Database tables missing. Run sql/001_registry_jobs.sql.",
    )


class IngestResponse(BaseModel):
    job_ids: list[str]


class ApproveRequest(BaseModel):
    job_id: str = Field(min_length=1)
    vendor_name: str = Field(min_length=1)
    schema_definition: dict


# ---------------------------------------------------------------------------
# POST /ingest
# ---------------------------------------------------------------------------

@router.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile) -> IngestResponse:
    settings = get_settings()

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    if not settings.database_url:
        raise HTTPException(status_code=500, detail="Database URL not configured")
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status_code=500, detail="Supabase Storage not configured")

    storage = SupabaseStorage(
        settings.supabase_url,
        settings.supabase_service_role_key,
        timeout_s=settings.storage_upload_timeout_s,
    )

    job_id = str(uuid.uuid4())

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / f"{job_id}.pdf"
            
            content = await file.read()
            if not content:
                logger.error("step=ingest status=failed reason=empty_file")
                raise HTTPException(status_code=400, detail="Uploaded file is empty")

            logger.info("step=ingest action=save_tmp file_size=%s", len(content))
            async with aiofiles.open(target_path, "wb") as f:
                await f.write(content)

            split_paths = split_pdf(target_path, output_dir=Path(tmpdir))

            jobs = SupabaseJobsRepository(settings.database_url)
            queue = RedisQueue.from_settings(settings)
            job_ids: list[str] = []
            jobs_to_create: list[dict[str, str]] = []

            try:
                upload_tasks = []
                sp_job_ids = []
                for split_index, sp in enumerate(split_paths, start=1):
                    sp_job_id = str(uuid.uuid4())
                    sp_job_ids.append(sp_job_id)
                    split_name = Path(sp).name
                    logger.info(
                        "step=ingest split_process status=start split_index=%s total_splits=%s split_file=%s",
                        split_index,
                        len(split_paths),
                        split_name,
                    )
                    file_bytes = Path(sp).read_bytes()
                    upload_tasks.append(storage.upload(f"{sp_job_id}.pdf", file_bytes))

                try:
                    # ⚡ Bolt Optimization:
                    # Execute all storage uploads concurrently using asyncio.gather
                    # This replaces the N+1 sequential await calls inside the loop,
                    # reducing total upload time from O(N) to roughly O(1) for split PDFs.
                    public_urls = await asyncio.gather(*upload_tasks)
                except Exception as exc:
                    logger.exception(
                        "step=ingest split_process status=failed phase=upload total_splits=%s",
                        len(split_paths),
                    )
                    raise SplitEnqueueError(phase="upload", split_file="multiple_splits", original_error=exc) from exc

                for sp_job_id, public_url in zip(sp_job_ids, public_urls):
                    jobs_to_create.append(
                        {
                            "job_id": sp_job_id,
                            "file_url": public_url,
                            "file_path": public_url,
                        }
                    )
                    job_ids.append(sp_job_id)

                if jobs_to_create:
                    try:
                        await jobs.create_jobs_bulk(jobs_to_create)
                    except Exception as exc:
                        logger.exception(
                            "step=ingest split_process status=failed phase=create_jobs_bulk total_splits=%s",
                            len(split_paths),
                        )
                        raise SplitEnqueueError(phase="create_jobs_bulk", split_file="all_splits", original_error=exc) from exc

                    try:
                        await queue.enqueue_jobs_bulk(jobs_to_create)
                    except Exception as exc:
                        logger.exception(
                            "step=ingest split_process status=failed phase=enqueue_jobs_bulk total_splits=%s",
                            len(split_paths),
                        )
                        raise SplitEnqueueError(phase="enqueue_jobs_bulk", split_file="all_splits", original_error=exc) from exc
            except Exception as exc:
                logger.exception("step=ingest enqueue_failed count=%s", len(job_ids))
                for jid in job_ids:
                    try:
                        await jobs.mark_failed(jid, f"Enqueue failed: {exc}")
                    except Exception:
                        pass
                if isinstance(exc, SplitEnqueueError):
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            f"Split/enqueue failed during {exc.phase} for {exc.split_file}: "
                            f"{exc.original_error}"
                        ),
                    ) from exc
                raise HTTPException(status_code=500, detail=f"Split/enqueue failed: {exc}") from exc
            finally:
                await queue.close()
    except asyncpg.PostgresError as exc:
        logger.exception("step=ingest status=failed job_id=%s error=%s", job_id, str(exc))
        _raise_if_missing_supabase_tables(exc)
        raise HTTPException(status_code=502, detail="Database API error") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("step=ingest status=failed job_id=%s", job_id)
        raise HTTPException(status_code=500, detail="Ingest failed") from exc

    return IngestResponse(job_ids=job_ids)


# ---------------------------------------------------------------------------
# GET /jobs  (list)
# ---------------------------------------------------------------------------

@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(status_code=500, detail="Database URL not configured")

    jobs = SupabaseJobsRepository(settings.database_url)
    try:
        return await jobs.list_jobs(status=status, limit=limit, offset=offset)
    except asyncpg.PostgresError as exc:
        logger.exception("step=list_jobs status=failed error=%s", str(exc))
        _raise_if_missing_supabase_tables(exc)
        raise HTTPException(status_code=502, detail="Database API error") from exc


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict:
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(status_code=500, detail="Database URL not configured")

    jobs = SupabaseJobsRepository(settings.database_url)

    try:
        job = await jobs.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except asyncpg.PostgresError as exc:
        logger.exception("step=get_job status=failed job_id=%s error=%s", job_id, str(exc))
        _raise_if_missing_supabase_tables(exc)
        raise HTTPException(status_code=502, detail="Database API error") from exc


# ---------------------------------------------------------------------------
# POST /approve
# ---------------------------------------------------------------------------

@router.post("/approve")
async def approve(payload: ApproveRequest) -> dict:
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(status_code=500, detail="Database URL not configured")

    try:
        registry = SupabaseRegistryRepository(settings.database_url)
        jobs = SupabaseJobsRepository(settings.database_url)

        job = await jobs.get_job(payload.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        extracted = job.get("extracted_data") or {}
        fingerprint_hash = extracted.get("fingerprint_hash")
        ocr_text_cache = extracted.get("ocr_text_cache")

        vendor_name_to_save = job.get("vendor_detected") or payload.vendor_name

        await registry.upsert_schema(
            vendor_name=vendor_name_to_save,
            fingerprint_hash=fingerprint_hash,
            ocr_text_cache=ocr_text_cache,
            schema_definition=payload.schema_definition,
        )

        await jobs.mark_requeued(job_id=payload.job_id, vendor_detected=payload.vendor_name)

        queue = RedisQueue.from_settings(settings)
        try:
            file_path = await jobs.get_file_url(payload.job_id)
            if not file_path:
                raise HTTPException(status_code=404, detail="Job not found")
            await queue.enqueue_job(job_id=payload.job_id, file_path=file_path)
        finally:
            await queue.close()
    except asyncpg.PostgresError as exc:
        logger.exception("step=approve status=failed job_id=%s error=%s", payload.job_id, str(exc))
        _raise_if_missing_supabase_tables(exc)
        raise HTTPException(status_code=502, detail="Database API error") from exc

    return {"status": "queued", "job_id": payload.job_id}


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@router.get("/health")
async def health() -> dict:
    settings = get_settings()

    report: dict[str, object] = {
        "status": "ok",
        "redis": {"ok": False},
        "supabase": {"ok": False},
    }

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis_client.ping()
        report["redis"] = {"ok": True}
    except Exception as exc:
        report["redis"] = {"ok": False, "error": str(exc)}
        report["status"] = "degraded"
    finally:
        await redis_client.aclose()

    if not settings.database_url:
        report["supabase"] = {"ok": False, "status": "disabled"}
        report["status"] = "degraded"
        return report

    async def _check_tables() -> dict[str, object]:
        try:
            # ⚡ Bolt Optimization:
            # Reusing the shared connection pool for the health check instead of
            # opening a new direct connection via asyncpg.connect(). This prevents
            # expensive TCP/TLS handshake and database authentication overhead,
            # significantly reducing latency on high-frequency health probes.
            pool = await get_connection_pool(settings.database_url)
            async with pool.acquire() as conn:
                await conn.execute("SELECT job_id FROM processing_jobs LIMIT 1")
                await conn.execute("SELECT id FROM document_registry LIMIT 1")
                return {"ok": True}
        except asyncpg.PostgresError as exc:
            code = getattr(exc, "sqlstate", "")
            return {"ok": False, "error": str(exc), "code": code}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    supabase_result = await _check_tables()
    report["supabase"] = supabase_result
    if not bool(supabase_result.get("ok")):
        report["status"] = "degraded"

    return report
