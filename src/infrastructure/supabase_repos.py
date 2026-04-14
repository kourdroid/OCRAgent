from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from supabase import Client, create_client

from src.config import Settings


def get_supabase_client(settings: Settings) -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


class SupabaseRegistryRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    async def get_vendor(self, vendor_name: str) -> Optional[dict[str, Any]]:
        def _query() -> Optional[dict[str, Any]]:
            response = self._client.table("document_registry").select("*").eq("vendor_name", vendor_name).execute()
            if not response.data:
                return None
            return response.data[0]

        return await asyncio.to_thread(_query)

    async def upsert_schema(self, vendor_name: str, schema_definition: dict[str, Any]) -> None:
        payload = {
            "vendor_name": vendor_name,
            "schema_definition": schema_definition,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        def _upsert() -> None:
            self._client.table("document_registry").upsert(payload).execute()

        await asyncio.to_thread(_upsert)


class SupabaseJobsRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    async def create_job(self, *, job_id: str, file_url: str) -> None:
        payload = {
            "job_id": job_id,
            "status": "PENDING",
            "file_url": file_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        def _insert() -> None:
            self._client.table("processing_jobs").insert(payload).execute()

        await asyncio.to_thread(_insert)

    async def get_file_url(self, job_id: str) -> Optional[str]:
        def _query() -> Optional[str]:
            response = self._client.table("processing_jobs").select("file_url").eq("job_id", job_id).execute()
            if not response.data:
                return None
            return response.data[0].get("file_url")

        return await asyncio.to_thread(_query)

    async def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        def _query() -> Optional[dict[str, Any]]:
            response = self._client.table("processing_jobs").select("*").eq("job_id", job_id).execute()
            if not response.data:
                return None
            return response.data[0]

        return await asyncio.to_thread(_query)

    async def mark_processing(self, job_id: str, vendor_detected: Optional[str]) -> None:
        await self._update_job(job_id, {"status": "PROCESSING", "vendor_detected": vendor_detected})

    async def mark_waiting_human(self, job_id: str, vendor_detected: Optional[str], proposed_schema: dict[str, Any]) -> None:
        await self._update_job(
            job_id,
            {
                "status": "WAITING_HUMAN",
                "vendor_detected": vendor_detected,
                "extracted_data": {"proposed_schema": proposed_schema},
            },
        )

    async def mark_completed(self, job_id: str, vendor_detected: Optional[str], extracted_data: dict[str, Any]) -> None:
        await self._update_job(job_id, {"status": "COMPLETED", "vendor_detected": vendor_detected, "extracted_data": extracted_data})

    async def mark_failed(self, job_id: str, error_log: str) -> None:
        await self._update_job(job_id, {"status": "FAILED", "error_log": error_log})

    async def mark_requeued(self, job_id: str, vendor_detected: Optional[str]) -> None:
        await self._update_job(job_id, {"status": "PENDING", "vendor_detected": vendor_detected})

    async def _update_job(self, job_id: str, patch: dict[str, Any]) -> None:
        patch = {**patch, "updated_at": datetime.now(timezone.utc).isoformat()}

        def _update() -> None:
            self._client.table("processing_jobs").update(patch).eq("job_id", job_id).execute()

        await asyncio.to_thread(_update)

