from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Optional

import asyncpg

from src.config import Settings


class SupabaseRegistryRepository:
    def __init__(self, conn_str: str) -> None:
        self.conn_str = conn_str

    async def get_vendor_schemas(self, vendor_name: str) -> list[dict[str, Any]]:
        conn = await asyncpg.connect(self.conn_str, statement_cache_size=0)
        try:
            rows = await conn.fetch(
                "SELECT * FROM document_registry WHERE vendor_name = $1", vendor_name
            )
            result = []
            for row in rows:
                data = dict(row)
                if data.get("schema_definition") and isinstance(data["schema_definition"], str):
                    data["schema_definition"] = json.loads(data["schema_definition"])
                result.append(data)
            return result
        finally:
            await conn.close()

    async def upsert_schema(self, vendor_name: str, fingerprint_hash: str, ocr_text_cache: str, schema_definition: dict[str, Any]) -> None:
        conn = await asyncpg.connect(self.conn_str, statement_cache_size=0)
        try:
            await conn.execute(
                """
                INSERT INTO document_registry (vendor_name, fingerprint_hash, ocr_text_cache, schema_definition, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (vendor_name, fingerprint_hash) DO UPDATE SET
                    schema_definition = EXCLUDED.schema_definition,
                    ocr_text_cache = EXCLUDED.ocr_text_cache,
                    schema_version = document_registry.schema_version + 1,
                    is_active = EXCLUDED.is_active
                """,
                vendor_name,
                fingerprint_hash,
                ocr_text_cache,
                json.dumps(schema_definition),
                True,
                datetime.now(timezone.utc)
            )
        finally:
            await conn.close()


class SupabaseJobsRepository:
    def __init__(self, conn_str: str) -> None:
        self.conn_str = conn_str

    async def create_job(self, *, job_id: str, file_url: str) -> None:
        conn = await asyncpg.connect(self.conn_str, statement_cache_size=0)
        try:
            await conn.execute(
                """
                INSERT INTO processing_jobs (job_id, status, file_url, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                job_id,
                "PENDING",
                file_url,
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
            )
        finally:
            await conn.close()

    async def get_file_url(self, job_id: str) -> Optional[str]:
        conn = await asyncpg.connect(self.conn_str, statement_cache_size=0)
        try:
            url = await conn.fetchval(
                "SELECT file_url FROM processing_jobs WHERE job_id = $1", job_id
            )
            return url
        finally:
            await conn.close()

    async def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        conn = await asyncpg.connect(self.conn_str, statement_cache_size=0)
        try:
            row = await conn.fetchrow(
                "SELECT * FROM processing_jobs WHERE job_id = $1", job_id
            )
            if not row:
                return None
            data = dict(row)
            if data.get("extracted_data") and isinstance(data["extracted_data"], str):
                data["extracted_data"] = json.loads(data["extracted_data"])
            return data
        finally:
            await conn.close()

    async def mark_processing(self, job_id: str, vendor_detected: Optional[str]) -> None:
        await self._update_job(job_id, {"status": "PROCESSING", "vendor_detected": vendor_detected})

    async def mark_waiting_human(self, job_id: str, vendor_detected: Optional[str], extracted_data: dict[str, Any]) -> None:
        await self._update_job(
            job_id,
            {
                "status": "WAITING_HUMAN",
                "vendor_detected": vendor_detected,
                "extracted_data": json.dumps(extracted_data),
            },
        )

    async def mark_completed(self, job_id: str, vendor_detected: Optional[str], extracted_data: dict[str, Any]) -> None:
        await self._update_job(job_id, {"status": "COMPLETED", "vendor_detected": vendor_detected, "extracted_data": json.dumps(extracted_data)})

    async def mark_failed(self, job_id: str, error_log: str) -> None:
        await self._update_job(job_id, {"status": "FAILED", "error_log": error_log})

    async def mark_requeued(self, job_id: str, vendor_detected: Optional[str]) -> None:
        await self._update_job(job_id, {"status": "PENDING", "vendor_detected": vendor_detected})

    async def _update_job(self, job_id: str, patch: dict[str, Any]) -> None:
        patch["updated_at"] = datetime.now(timezone.utc)
        
        conn = await asyncpg.connect(self.conn_str, statement_cache_size=0)
        try:
            set_clauses = []
            values = []
            
            for idx, (k, v) in enumerate(patch.items(), start=1):
                set_clauses.append(f"{k} = ${idx}")
                values.append(v)
                
            values.append(job_id)
            query = f"UPDATE processing_jobs SET {', '.join(set_clauses)} WHERE job_id = ${len(values)}"
            
            await conn.execute(query, *values)
        finally:
            await conn.close()


