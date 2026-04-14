from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

import redis.asyncio as redis
from redis.exceptions import ResponseError

from src.config import Settings


@dataclass(frozen=True)
class RedisMessage:
    message_id: str
    body: dict[str, Any]


class RedisQueue:
    def __init__(self, client: redis.Redis, *, stream_key: str, group: str, consumer: str) -> None:
        self._client = client
        self._stream_key = stream_key
        self._group = group
        self._consumer = consumer

    @classmethod
    def from_settings(cls, settings: Settings) -> "RedisQueue":
        client = redis.from_url(settings.redis_url, decode_responses=True)
        return cls(client, stream_key="ironclad:jobs", group="ironclad-workers", consumer="worker-1")

    async def ensure_group(self) -> None:
        try:
            await self._client.xgroup_create(name=self._stream_key, groupname=self._group, id="0", mkstream=True)
            return
        except ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                return
            raise

    async def enqueue_job(self, *, job_id: str, file_path: str) -> str:
        payload = {"job_id": job_id, "file_path": file_path}
        message_id = await self._client.xadd(self._stream_key, {"payload": json.dumps(payload)})
        return str(message_id)

    async def read_one(self, *, block_ms: int = 5000, count: int = 1) -> Optional[RedisMessage]:
        try:
            reply = await self._client.xreadgroup(
                groupname=self._group,
                consumername=self._consumer,
                block=block_ms,
                count=count,
                streams={self._stream_key: ">"},
            )
        except ResponseError as exc:
            if "NOGROUP" in str(exc):
                await self.ensure_group()
                return None
            raise
        if not reply:
            return None

        stream_name, messages = reply[0]
        if stream_name != self._stream_key or not messages:
            return None

        message_id, fields = messages[0]
        raw = fields.get("payload")
        body = json.loads(raw) if raw else {}
        return RedisMessage(message_id=str(message_id), body=body)

    async def ack(self, message_id: str) -> None:
        await self._client.xack(self._stream_key, self._group, message_id)

    async def close(self) -> None:
        await self._client.aclose()
