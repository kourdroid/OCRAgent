from __future__ import annotations

import asyncio
import logging

from src.config import get_settings
from src.infrastructure.dossier_repos import DossierRepository
from src.infrastructure.redis_queue import RedisQueue
from src.infrastructure.supabase_repos import close_connection_pool, get_connection_pool

logger = logging.getLogger(__name__)


async def run_dispatcher() -> None:
    settings = get_settings()
    if not settings.database_url:
        raise ValueError("DATABASE_URL is not configured")

    pool = await get_connection_pool(settings.database_url)
    repository = DossierRepository(pool)
    queue = RedisQueue.from_settings(settings)
    await queue.ensure_group()

    try:
        while True:
            events = await repository.claim_outbox_events(limit=20)
            if not events:
                await asyncio.sleep(1.0)
                continue
            for event in events:
                event_id = str(event["event_id"])
                try:
                    await queue.enqueue_payload(event["payload"])
                    await repository.mark_outbox_published(event_id)
                except Exception as exc:
                    logger.exception(
                        "step=outbox_publish status=failed event_id=%s",
                        event_id,
                    )
                    await repository.release_outbox_event(event_id, str(exc))
    finally:
        await queue.close()
        await close_connection_pool(settings.database_url)


def main() -> None:
    asyncio.run(run_dispatcher())


if __name__ == "__main__":
    main()
