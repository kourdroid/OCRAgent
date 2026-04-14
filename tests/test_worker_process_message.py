from __future__ import annotations

import pytest

from src.worker.worker import _process_message


class DummyQueue:
    def __init__(self) -> None:
        self.acked: list[str] = []

    async def ack(self, message_id: str) -> None:
        self.acked.append(message_id)


class DummyJobs:
    def __init__(self, *, fail_mark_failed: bool) -> None:
        self.fail_mark_failed = fail_mark_failed
        self.failed: list[tuple[str, str]] = []

    async def mark_failed(self, job_id: str, error_log: str) -> None:
        if self.fail_mark_failed:
            raise OSError("dns failure")
        self.failed.append((job_id, error_log))


class DummyGraph:
    def __init__(self, *, fail: bool) -> None:
        self.fail = fail

    async def ainvoke(self, *_args, **_kwargs):
        if self.fail:
            raise RuntimeError("boom")
        return {"ok": True}


@pytest.mark.asyncio
async def test_process_message_acks_on_success() -> None:
    queue = DummyQueue()
    jobs = DummyJobs(fail_mark_failed=False)
    graph = DummyGraph(fail=False)

    await _process_message(
        graph=graph,
        jobs=jobs,
        queue=queue,
        message_id="1-0",
        job_id="job-1",
        file_path="/tmp/file.pdf",
    )

    assert queue.acked == ["1-0"]
    assert jobs.failed == []


@pytest.mark.asyncio
async def test_process_message_acks_even_if_mark_failed_fails() -> None:
    queue = DummyQueue()
    jobs = DummyJobs(fail_mark_failed=True)
    graph = DummyGraph(fail=True)

    await _process_message(
        graph=graph,
        jobs=jobs,
        queue=queue,
        message_id="2-0",
        job_id="job-2",
        file_path="/tmp/file.pdf",
    )

    assert queue.acked == ["2-0"]

