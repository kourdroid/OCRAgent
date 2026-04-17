from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Optional

import asyncpg


_shared_pools: dict[str, asyncpg.Pool] = {}
_pool_lock: asyncio.Lock | None = None


async def _get_pool_lock() -> asyncio.Lock:
    global _pool_lock
    if _pool_lock is None:
        _pool_lock = asyncio.Lock()
    return _pool_lock


async def get_connection_pool(
    conn_str: str,
    *,
    min_size: int = 1,
    max_size: int = 10,
) -> asyncpg.Pool:
    pool = _shared_pools.get(conn_str)
    if pool is not None:
        return pool

    lock = await _get_pool_lock()
    async with lock:
        pool = _shared_pools.get(conn_str)
        if pool is not None:
            return pool

        pool = await asyncpg.create_pool(
            dsn=conn_str,
            min_size=min_size,
            max_size=max_size,
            statement_cache_size=0,
        )
        _shared_pools[conn_str] = pool
        return pool


async def close_connection_pool(conn_str: str) -> None:
    pool = _shared_pools.pop(conn_str, None)
    if pool is not None:
        await pool.close()


class _BaseRepository:
    def __init__(self, db: str | asyncpg.Pool) -> None:
        self._conn_str = db if isinstance(db, str) else None
        self._pool = db if isinstance(db, asyncpg.Pool) else None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is not None:
            return self._pool
        if not self._conn_str:
            raise RuntimeError("Database pool is not configured")
        self._pool = await get_connection_pool(self._conn_str)
        return self._pool


class SupabaseRegistryRepository(_BaseRepository):
    def __init__(self, db: str | asyncpg.Pool) -> None:
        super().__init__(db)

    async def get_vendor_schemas(self, vendor_name: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
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

    async def upsert_schema(self, vendor_name: str, fingerprint_hash: str, ocr_text_cache: str, schema_definition: dict[str, Any]) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
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

    async def get_po_lines(self, po_number: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM erp_po_lines WHERE po_number = $1", po_number
            )
            return [dict(r) for r in rows]

    async def get_goods_receipts(self, po_number: str) -> list[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM erp_goods_receipts WHERE po_number = $1", po_number
            )
            return [dict(r) for r in rows]


class SupabaseJobsRepository(_BaseRepository):
    def __init__(self, db: str | asyncpg.Pool) -> None:
        super().__init__(db)

    async def create_job(self, *, job_id: str, file_url: str) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
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

    async def get_file_url(self, job_id: str) -> Optional[str]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            url = await conn.fetchval(
                "SELECT file_url FROM processing_jobs WHERE job_id = $1", job_id
            )
            return url

    async def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM processing_jobs WHERE job_id = $1", job_id
            )
            if not row:
                return None
            data = dict(row)
            if data.get("extracted_data") and isinstance(data["extracted_data"], str):
                data["extracted_data"] = json.loads(data["extracted_data"])
            return data

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

    async def mark_delivery_failed(
        self,
        job_id: str,
        error_log: str,
        extracted_data: dict[str, Any] | None = None,
    ) -> None:
        patch: dict[str, Any] = {
            "status": "DELIVERY_FAILED",
            "error_log": error_log,
        }
        if extracted_data is not None:
            patch["extracted_data"] = json.dumps(extracted_data)
        await self._update_job(job_id, patch)

    async def mark_requeued(self, job_id: str, vendor_detected: Optional[str]) -> None:
        await self._update_job(job_id, {"status": "PENDING", "vendor_detected": vendor_detected})

    async def _update_job(self, job_id: str, patch: dict[str, Any]) -> None:
        patch["updated_at"] = datetime.now(timezone.utc)

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            set_clauses = []
            values = []

            for idx, (k, v) in enumerate(patch.items(), start=1):
                set_clauses.append(f"{k} = ${idx}")
                values.append(v)

            values.append(job_id)
            query = f"UPDATE processing_jobs SET {', '.join(set_clauses)} WHERE job_id = ${len(values)}"

            await conn.execute(query, *values)
