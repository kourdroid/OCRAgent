from __future__ import annotations

import pytest

from src.providers.base import RetryableProviderError
from src.worker.worker import _process_dossier_message


class _Queue:
    def __init__(self) -> None:
        self.acked: list[str] = []

    async def ack(self, message_id: str) -> None:
        self.acked.append(message_id)


class _Processor:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    async def process_source(self, **_kwargs) -> None:
        if self.error:
            raise self.error


class _Repository:
    def __init__(self, *, fail_persistence: bool = False) -> None:
        self.fail_persistence = fail_persistence
        self.retried: list[str] = []
        self.failed: list[str] = []

    async def schedule_retry(self, *, job_id: str, **_kwargs) -> bool:
        if self.fail_persistence:
            raise OSError("database unavailable")
        self.retried.append(job_id)
        return True

    async def mark_job_failed(self, *, job_id: str, **_kwargs) -> None:
        if self.fail_persistence:
            raise OSError("database unavailable")
        self.failed.append(job_id)


async def _run(
    processor: _Processor,
    repository: _Repository,
    queue: _Queue,
) -> None:
    await _process_dossier_message(
        processor=processor,  # type: ignore[arg-type]
        repository=repository,  # type: ignore[arg-type]
        queue=queue,
        message_id="1-0",
        job_id="job-1",
        case_id="case-1",
        client_id="delassus",
        workflow_id="morocco_import_dossier",
        file_path="https://storage/document.pdf",
    )


@pytest.mark.asyncio
async def test_dossier_worker_acks_success() -> None:
    queue = _Queue()
    repository = _Repository()

    await _run(_Processor(), repository, queue)

    assert queue.acked == ["1-0"]


@pytest.mark.asyncio
async def test_dossier_worker_persists_retry_before_ack() -> None:
    queue = _Queue()
    repository = _Repository()

    await _run(
        _Processor(RetryableProviderError("rate limited")),
        repository,
        queue,
    )

    assert repository.retried == ["job-1"]
    assert queue.acked == ["1-0"]


@pytest.mark.asyncio
async def test_dossier_worker_does_not_ack_when_retry_persistence_fails() -> None:
    queue = _Queue()
    repository = _Repository(fail_persistence=True)

    await _run(
        _Processor(RetryableProviderError("rate limited")),
        repository,
        queue,
    )

    assert queue.acked == []
