from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

import aiofiles
import asyncpg
import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.config import get_settings
from src.infrastructure.redis_queue import RedisQueue
from src.infrastructure.supabase_repos import SupabaseJobsRepository, SupabaseRegistryRepository

router = APIRouter()
logger = logging.getLogger(__name__)


def _raise_if_missing_supabase_tables(exc: asyncpg.PostgresError) -> None:
    code = getattr(exc, "sqlstate", "")
    if code != "42P01": # undefined_table
        return
    raise HTTPException(
        status_code=503,
        detail="Database tables missing. Run sql/001_registry_jobs.sql.",
    )


class IngestResponse(BaseModel):
    job_id: str


class ApproveRequest(BaseModel):
    job_id: str = Field(min_length=1)
    vendor_name: str = Field(min_length=1)
    schema_definition: dict


@router.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile) -> IngestResponse:
    settings = get_settings()

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    job_id = str(uuid4())
    target_path = settings.uploads_dir / f"{job_id}.pdf"
    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with aiofiles.open(target_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        if not settings.database_url:
            raise HTTPException(status_code=500, detail="Database URL not configured")

        jobs = SupabaseJobsRepository(settings.database_url)
        await jobs.create_job(job_id=job_id, file_url=str(target_path))

        queue = RedisQueue.from_settings(settings)
        try:
            await queue.enqueue_job(job_id=job_id, file_path=str(target_path))
        except Exception:
            await jobs.mark_failed(job_id, "Job created but enqueue to Redis failed")
            raise
        finally:
            await queue.close()
    except asyncpg.PostgresError as exc:
        logger.exception("step=ingest status=failed job_id=%s error=%s", job_id, str(exc))
        try:
            target_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("step=ingest cleanup=failed file=%s", target_path)
        _raise_if_missing_supabase_tables(exc)
        raise HTTPException(status_code=502, detail="Database API error") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("step=ingest status=failed job_id=%s", job_id)
        raise HTTPException(status_code=500, detail="Ingest failed") from exc

    return IngestResponse(job_id=job_id)


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

        await registry.upsert_schema(
            vendor_name=payload.vendor_name,
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
            conn = await asyncpg.connect(settings.database_url, statement_cache_size=0)
            try:
                await conn.execute("SELECT job_id FROM processing_jobs LIMIT 1")
                await conn.execute("SELECT id FROM document_registry LIMIT 1")
                return {"ok": True}
            finally:
                await conn.close()
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
