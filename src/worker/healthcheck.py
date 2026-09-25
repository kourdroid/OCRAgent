from __future__ import annotations

import asyncio
import os

import asyncpg
import redis.asyncio as redis

from src.config import get_settings
from src.providers.factory import build_document_provider


def _provider_check_enabled() -> bool:
    return os.getenv("CHECK_DOCUMENT_PROVIDER", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


async def check_dependencies() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis_client.ping()
    finally:
        await redis_client.aclose()

    connection = await asyncpg.connect(
        settings.database_url,
        statement_cache_size=0,
        ssl="require",
        timeout=5.0,
    )
    try:
        await connection.execute("SELECT 1")
    finally:
        await connection.close()

    if _provider_check_enabled():
        provider = build_document_provider(settings)
        result = await provider.healthcheck()
        if not result.get("ok"):
            raise RuntimeError("Document provider is not ready")


def main() -> None:
    asyncio.run(check_dependencies())


if __name__ == "__main__":
    main()
