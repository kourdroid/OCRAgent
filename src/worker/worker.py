from __future__ import annotations

import asyncio
import logging
from typing import Any

import asyncpg
from langgraph.checkpoint.memory import InMemorySaver

from src.config import get_settings
from src.core.graph import GraphDeps, build_graph
from src.dossiers.processor import DossierProcessor
from src.infrastructure.dossier_repos import DossierRepository
from src.infrastructure.redis_queue import RedisQueue
from src.infrastructure.supabase_repos import (
    SupabaseJobsRepository,
    SupabaseRegistryRepository,
    close_connection_pool,
    get_connection_pool,
)
from src.infrastructure.webhook_client import HttpWebhookClient, WebhookDeliveryError
from src.plugins.base import DEFAULT_CLIENT_ID
from src.plugins.registry import DEFAULT_WORKFLOW_REGISTRY
from src.providers.base import RetryableProviderError
from src.providers.factory import build_document_provider

logger = logging.getLogger(__name__)

_PENDING_RETRY_IDLE_MS = 10 * 60 * 1000
_PENDING_RECOVERY_INTERVAL_S = 30.0


async def _handle_queue_message(
    *,
    graph: Any,
    jobs: Any,
    queue: Any,
    msg: Any,
    dossier_processor: DossierProcessor | None = None,
    dossier_repository: DossierRepository | None = None,
) -> None:
    job_id = msg.body.get("job_id")
    file_path = msg.body.get("file_path")
    client_id = msg.body.get("client_id") or DEFAULT_CLIENT_ID
    if not job_id or not file_path:
        await queue.ack(msg.message_id)
        return

    case_id = msg.body.get("case_id")
    document_artifact_id = msg.body.get("document_artifact_id")
    workflow_id = msg.body.get("workflow_id")
    if case_id or document_artifact_id or workflow_id:
        if (
            not case_id
            or not document_artifact_id
            or not workflow_id
            or dossier_processor is None
            or dossier_repository is None
        ):
            logger.error(
                "job=%s step=dossier_message status=invalid action=ack",
                job_id,
            )
            await queue.ack(msg.message_id)
            return
        await _process_dossier_message(
            processor=dossier_processor,
            repository=dossier_repository,
            queue=queue,
            message_id=msg.message_id,
            job_id=job_id,
            case_id=case_id,
            client_id=client_id,
            workflow_id=workflow_id,
            file_path=file_path,
        )
        return

    await _process_message(
        graph=graph,
        jobs=jobs,
        queue=queue,
        message_id=msg.message_id,
        job_id=job_id,
        client_id=client_id,
        file_path=file_path,
    )


async def _process_dossier_message(
    *,
    processor: DossierProcessor,
    repository: DossierRepository,
    queue: Any,
    message_id: str,
    job_id: str,
    case_id: str,
    client_id: str,
    workflow_id: str,
    file_path: str,
) -> None:
    try:
        await processor.process_source(
            job_id=job_id,
            case_id=case_id,
            client_id=client_id,
            workflow_id=workflow_id,
            file_path=file_path,
        )
    except (RetryableProviderError, TimeoutError, ConnectionError, asyncpg.PostgresError) as exc:
        logger.warning(
            "job=%s case=%s step=dossier_process status=transient error=%s",
            job_id,
            case_id,
            str(exc),
        )
        try:
            await repository.schedule_retry(
                job_id=job_id,
                client_id=client_id,
                error=str(exc),
            )
        except Exception:
            logger.exception(
                "job=%s case=%s step=dossier_retry status=persist_failed",
                job_id,
                case_id,
            )
            return
    except Exception as exc:
        logger.exception(
            "job=%s case=%s step=dossier_process status=fatal",
            job_id,
            case_id,
        )
        try:
            await repository.mark_job_failed(
                job_id=job_id,
                client_id=client_id,
                error=str(exc),
            )
        except Exception:
            logger.exception(
                "job=%s case=%s step=dossier_failure status=persist_failed",
                job_id,
                case_id,
            )
            return

    try:
        await queue.ack(message_id)
    except Exception:
        logger.exception(
            "job=%s case=%s step=dossier_ack status=failed",
            job_id,
            case_id,
        )


async def _process_message(
    *,
    graph: Any,
    jobs: Any,
    queue: Any,
    message_id: str,
    job_id: str,
    file_path: str,
    client_id: str = DEFAULT_CLIENT_ID,
) -> None:
    ack_needed = True
    try:
        await graph.ainvoke(
            {"job_id": job_id, "client_id": client_id, "file_path": file_path},
            {"configurable": {"thread_id": job_id}},
        )
    except WebhookDeliveryError as exc:
        logger.error(
            "job=%s step=process_message status=delivery_failed action=ack error=%s",
            job_id,
            str(exc),
        )
    except Exception as exc:
        is_transient = False

        # 1. Check common network/timeout errors
        if isinstance(exc, (TimeoutError, ConnectionError)):
            is_transient = True

        # 2. Check for API errors that expose numeric status codes.
        code = getattr(exc, "code", None)
        if code == 429 or (isinstance(code, int) and code >= 500):
            is_transient = True

        # 3. Check message string for keywords
        msg_str = str(exc).lower()
        if "resource_exhausted" in msg_str or "rate limit" in msg_str or "timed out" in msg_str:
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
                ack_needed = False
            
    finally:
        if ack_needed:
            try:
                await queue.ack(message_id)
            except Exception:
                logger.exception("job=%s step=ack status=failed message_id=%s", job_id, message_id)


async def run_worker() -> None:
    settings = get_settings()

    if not settings.database_url:
        raise ValueError("DATABASE_URL is not configured")

    pool = await get_connection_pool(settings.database_url)
    registry = SupabaseRegistryRepository(pool)
    jobs = SupabaseJobsRepository(pool)
    dossier_repository = DossierRepository(pool)
    webhook = HttpWebhookClient(settings.webhook_url, jobs=jobs)
    provider = build_document_provider(settings)
    logger.info(
        "step=document_provider status=ready provider=%s model=%s",
        getattr(provider, "provider_id", settings.document_provider),
        getattr(provider, "model_id", settings.model_name),
    )
    dossier_processor = DossierProcessor(
        repository=dossier_repository,
        provider=provider,
        workflow_registry=DEFAULT_WORKFLOW_REGISTRY,
    )

    deps = GraphDeps(
        registry=registry,
        jobs=jobs,
        webhook=webhook,
        drift_threshold=settings.drift_threshold,
    )
    graph = build_graph(deps, checkpointer=InMemorySaver())

    queue = RedisQueue.from_settings(settings)
    await queue.ensure_group()
    loop = asyncio.get_running_loop()
    last_recovery_run = 0.0

    try:
        while True:
            now = loop.time()
            if now - last_recovery_run >= _PENDING_RECOVERY_INTERVAL_S:
                last_recovery_run = now
                claimed_messages = await queue.claim_idle_messages(min_idle_ms=_PENDING_RETRY_IDLE_MS)
                if claimed_messages:
                    logger.warning(
                        "step=queue_recovery status=claimed count=%s idle_ms=%s",
                        len(claimed_messages),
                        _PENDING_RETRY_IDLE_MS,
                    )
                    for msg in claimed_messages:
                        await _handle_queue_message(
                            graph=graph,
                            jobs=jobs,
                            queue=queue,
                            msg=msg,
                            dossier_processor=dossier_processor,
                            dossier_repository=dossier_repository,
                        )
                    continue

            msg = await queue.read_one()
            if not msg:
                continue

            await _handle_queue_message(
                graph=graph,
                jobs=jobs,
                queue=queue,
                msg=msg,
                dossier_processor=dossier_processor,
                dossier_repository=dossier_repository,
            )
    finally:
        await webhook.close()
        await queue.close()
        await close_connection_pool(settings.database_url)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
