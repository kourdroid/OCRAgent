from __future__ import annotations

import json
import os
import socket
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
    def __init__(
        self,
        client: redis.Redis,
        *,
        stream_key: str,
        group: str,
        consumer: str,
        reclaim_min_idle_ms: int = 600_000,
        claim_batch_size: int = 10,
    ) -> None:
        self._client = client
        self._stream_key = stream_key
        self._group = group
        self._consumer = consumer
        self._reclaim_min_idle_ms = reclaim_min_idle_ms
        self._claim_batch_size = claim_batch_size
        self._claim_cursor = "0-0"

    @classmethod
    def from_settings(cls, settings: Settings) -> "RedisQueue":
        client = redis.from_url(settings.redis_url, decode_responses=True)
        consumer = f"{socket.gethostname()}-{os.getpid()}"
        return cls(client, stream_key="ironclad:jobs", group="ironclad-workers", consumer=consumer)

    def _parse_message(self, message_id: Any, fields: Any) -> RedisMessage:
        raw = fields.get("payload") if isinstance(fields, dict) else None
        body = json.loads(raw) if raw else {}
        return RedisMessage(message_id=str(message_id), body=body)

    def _parse_autoclaim_reply(self, reply: Any) -> tuple[str, list[RedisMessage]]:
        if not isinstance(reply, (list, tuple)) or len(reply) < 2:
            return "0-0", []

        next_cursor = str(reply[0] or "0-0")
        messages = reply[1] or []
        parsed = [self._parse_message(message_id, fields) for message_id, fields in messages]
        return next_cursor, parsed

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
        return self._parse_message(message_id, fields)

    async def claim_idle_messages(
        self,
        *,
        min_idle_ms: int | None = None,
        count: int | None = None,
    ) -> list[RedisMessage]:
        try:
            reply = await self._client.xautoclaim(
                name=self._stream_key,
                groupname=self._group,
                consumername=self._consumer,
                min_idle_time=min_idle_ms or self._reclaim_min_idle_ms,
                start_id=self._claim_cursor,
                count=count or self._claim_batch_size,
            )
        except ResponseError as exc:
            if "NOGROUP" in str(exc):
                await self.ensure_group()
                return []
            raise

        next_cursor, messages = self._parse_autoclaim_reply(reply)
        self._claim_cursor = next_cursor
        if not messages and next_cursor == "0-0":
            self._claim_cursor = "0-0"
        return messages

    async def ack(self, message_id: str) -> None:
        await self._client.xack(self._stream_key, self._group, message_id)

    async def close(self) -> None:
        await self._client.aclose()
