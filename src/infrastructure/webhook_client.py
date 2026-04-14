from __future__ import annotations

from typing import Any, Optional

import httpx


class HttpWebhookClient:
    def __init__(self, webhook_url: Optional[str]) -> None:
        self._webhook_url = webhook_url

    async def send(self, job_id: str, payload: dict[str, Any]) -> None:
        if not self._webhook_url:
            return

        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(self._webhook_url, json={"job_id": job_id, "data": payload})

