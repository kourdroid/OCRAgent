from __future__ import annotations

import asyncio
import logging
import ast
from uuid import uuid4

import aiofiles
import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, UploadFile
from postgrest.exceptions import APIError as PostgrestAPIError
from pydantic import BaseModel, Field

from src.config import get_settings
from src.infrastructure.redis_queue import RedisQueue
from src.infrastructure.supabase_repos import SupabaseJobsRepository, SupabaseRegistryRepository, get_supabase_client

router = APIRouter()
logger = logging.getLogger(__name__)


def _postgrest_error_payload(exc: PostgrestAPIError) -> dict:
    if exc.args and isinstance(exc.args[0], dict):
        return exc.args[0]
    if exc.args and isinstance(exc.args[0], str):
        raw = exc.args[0]
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, dict):
                return parsed
        except (SyntaxError, ValueError):
            return {"message": raw}
    return {"message": str(exc)}


def _raise_if_missing_supabase_tables(exc: PostgrestAPIError) -> None:
    payload = _postgrest_error_payload(exc)
    code = payload.get("code")
    if code != "PGRST205" and "PGRST205" not in str(payload):
        return
    raise HTTPException(
        status_code=503,
        detail="Supabase tables missing. Run sql/001_registry_jobs.sql in this Supabase project and wait for schema cache refresh.",
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

        supabase = get_supabase_client(settings)
        jobs = SupabaseJobsRepository(supabase)
        await jobs.create_job(job_id=job_id, file_url=str(target_path))

        queue = RedisQueue.from_settings(settings)
        try:
            await queue.enqueue_job(job_id=job_id, file_path=str(target_path))
        except Exception:
            await jobs.mark_failed(job_id, "Job created but enqueue to Redis failed")
            raise
        finally:
            await queue.close()
    except PostgrestAPIError as exc:
        logger.exception("step=ingest status=failed job_id=%s error=%s", job_id, _postgrest_error_payload(exc))
        try:
            target_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("step=ingest cleanup=failed file=%s", target_path)
        _raise_if_missing_supabase_tables(exc)
        raise HTTPException(status_code=502, detail="Supabase API error") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("step=ingest status=failed job_id=%s", job_id)
        raise HTTPException(status_code=500, detail="Ingest failed") from exc

    return IngestResponse(job_id=job_id)


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict:
    settings = get_settings()
    supabase = get_supabase_client(settings)
    jobs = SupabaseJobsRepository(supabase)
    
    try:
        job = await jobs.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except PostgrestAPIError as exc:
        logger.exception("step=get_job status=failed job_id=%s error=%s", job_id, _postgrest_error_payload(exc))
        _raise_if_missing_supabase_tables(exc)
        raise HTTPException(status_code=502, detail="Supabase API error") from exc


@router.post("/approve")
async def approve(payload: ApproveRequest) -> dict:
    settings = get_settings()
    try:
        supabase = get_supabase_client(settings)

        registry = SupabaseRegistryRepository(supabase)
        jobs = SupabaseJobsRepository(supabase)

        await registry.upsert_schema(
            vendor_name=payload.vendor_name,
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
    except PostgrestAPIError as exc:
        logger.exception("step=approve status=failed job_id=%s error=%s", payload.job_id, _postgrest_error_payload(exc))
        _raise_if_missing_supabase_tables(exc)
        raise HTTPException(status_code=502, detail="Supabase API error") from exc

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

    if not settings.supabase_url or not settings.supabase_service_role_key:
        report["supabase"] = {"ok": False, "status": "disabled"}
        report["status"] = "degraded"
        return report

    supabase = get_supabase_client(settings)

    def _check_tables() -> dict[str, object]:
        try:
            supabase.table("processing_jobs").select("job_id").limit(1).execute()
            supabase.table("document_registry").select("id").limit(1).execute()
            return {"ok": True}
        except PostgrestAPIError as exc:
            payload = _postgrest_error_payload(exc)
            return {"ok": False, "error": payload}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    supabase_result = await asyncio.to_thread(_check_tables)
    report["supabase"] = supabase_result
    if not bool(supabase_result.get("ok")):
        report["status"] = "degraded"

    return report
