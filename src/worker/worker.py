from __future__ import annotations

import asyncio
import logging
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from src.config import get_settings
from src.core.graph import GraphDeps, build_graph
from src.infrastructure.redis_queue import RedisQueue
from src.infrastructure.supabase_repos import SupabaseJobsRepository, SupabaseRegistryRepository, get_supabase_client
from src.infrastructure.webhook_client import HttpWebhookClient

logger = logging.getLogger(__name__)


async def _process_message(*, graph: Any, jobs: Any, queue: Any, message_id: str, job_id: str, file_path: str) -> None:
    ack_needed = True
    try:
        await graph.ainvoke(
            {"job_id": job_id, "file_path": file_path},
            {"configurable": {"thread_id": job_id}},
        )
    except Exception as exc:
        is_transient = False
        
        # 1. Check common network/timeout errors
        if isinstance(exc, (TimeoutError, ConnectionError)):
            is_transient = True
            
        # 2. Check for Google API errors (duck typing)
        code = getattr(exc, "code", None)
        if code == 429 or (isinstance(code, int) and code >= 500):
            is_transient = True
            
        # 3. Check message string for keywords
        msg_str = str(exc).lower()
        if "resource_exhausted" in msg_str or "rate limit" in msg_str:
            is_transient = True
            
        if is_transient:
            logger.warning("job=%s step=process_message status=transient_error error=%s action=retry_later", job_id, str(exc))
            ack_needed = False
        else:
            logger.exception("job=%s step=process_message status=fatal_error error=%s action=mark_failed", job_id, str(exc))
            try:
                await jobs.mark_failed(job_id, str(exc))
            except Exception:
                logger.exception("job=%s step=mark_failed status=failed", job_id)
            
    finally:
        if ack_needed:
            try:
                await queue.ack(message_id)
            except Exception:
                logger.exception("job=%s step=ack status=failed message_id=%s", job_id, message_id)


async def run_worker() -> None:
    settings = get_settings()

    supabase = get_supabase_client(settings)
    registry = SupabaseRegistryRepository(supabase)
    jobs = SupabaseJobsRepository(supabase)
    webhook = HttpWebhookClient(settings.webhook_url)

    deps = GraphDeps(registry=registry, jobs=jobs, webhook=webhook)
    graph = build_graph(deps, checkpointer=InMemorySaver())

    queue = RedisQueue.from_settings(settings)
    await queue.ensure_group()

    while True:
        msg = await queue.read_one()
        if not msg:
            continue

        job_id = msg.body.get("job_id")
        file_path = msg.body.get("file_path")
        if not job_id or not file_path:
            await queue.ack(msg.message_id)
            continue

        await _process_message(
            graph=graph,
            jobs=jobs,
            queue=queue,
            message_id=msg.message_id,
            job_id=job_id,
            file_path=file_path,
        )


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
