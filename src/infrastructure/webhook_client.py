from __future__ import annotations

import logging
from typing import Any, Optional, Protocol

import httpx


logger = logging.getLogger(__name__)


class DeliveryStatusRepository(Protocol):
    async def mark_delivery_failed(
        self,
        job_id: str,
        error_log: str,
        extracted_data: dict[str, Any] | None = None,
    ) -> None: ...


class WebhookDeliveryError(RuntimeError):
    pass


class HttpWebhookClient:
    def __init__(
        self,
        webhook_url: Optional[str],
        *,
        jobs: DeliveryStatusRepository | None = None,
        timeout_s: float = 15.0,
    ) -> None:
        self._webhook_url = webhook_url
        self._jobs = jobs
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def send(self, job_id: str, payload: dict[str, Any]) -> None:
        if not self._webhook_url:
            return

        try:
            response = await self._client.post(self._webhook_url, json={"job_id": job_id, "data": payload})
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            error_message = f"Webhook returned HTTP {exc.response.status_code}: {exc}"
            logger.error(
                "job=%s step=deliver_webhook status=http_error status_code=%s url=%s",
                job_id,
                exc.response.status_code,
                self._webhook_url,
            )
            await self._mark_delivery_failed(job_id, error_message, payload)
            raise WebhookDeliveryError(error_message) from exc
        except httpx.RequestError as exc:
            error_message = f"Webhook request failed: {exc}"
            logger.error(
                "job=%s step=deliver_webhook status=request_error url=%s error=%s",
                job_id,
                self._webhook_url,
                str(exc),
            )
            await self._mark_delivery_failed(job_id, error_message, payload)
            raise WebhookDeliveryError(error_message) from exc

    async def _mark_delivery_failed(
        self,
        job_id: str,
        error_message: str,
        payload: dict[str, Any],
    ) -> None:
        if self._jobs is None:
            return

        try:
            await self._jobs.mark_delivery_failed(job_id, error_message, payload)
        except Exception:
            logger.exception("job=%s step=deliver_webhook status=delivery_failure_persist_failed", job_id)

    async def close(self) -> None:
        await self._client.aclose()
