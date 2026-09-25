from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src.api.app import app
from src.config import Settings


@dataclass
class DummyQueue:
    enqueued: list[dict[str, Any]]

    async def enqueue_jobs_bulk(self, jobs_data: list[dict[str, Any]]) -> list[str]:
        for job in jobs_data:
            self.enqueued.append(
                {
                    "job_id": job["job_id"],
                    "file_path": job["file_path"],
                    "client_id": job["client_id"],
                }
            )
        return [f"1-{i}" for i in range(len(jobs_data))]

    async def close(self) -> None:
        return None


@dataclass
class DummyJobsRepo:
    created: list[dict[str, Any]]
    failed: list[str]

    async def create_jobs_bulk(self, jobs_data: list[dict[str, Any]]) -> None:
        self.created.extend(jobs_data)

    async def mark_failed(self, job_id: str, error_log: str) -> None:
        self.failed.append(job_id)


class DummyStorage:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.timeout = 60.0

    async def upload(self, path: str, data: bytes, content_type: str = "application/pdf", client=None) -> str:
        return f"http://storage.example/{path}"


def test_ingest_creates_jobs_and_enqueues_every_split(tmp_path: Path, monkeypatch) -> None:
    split_one = tmp_path / "split_001.pdf"
    split_two = tmp_path / "split_002.pdf"
    split_one.write_bytes(b"%PDF-1.4 split 1")
    split_two.write_bytes(b"%PDF-1.4 split 2")

    settings = Settings(
        llm_api_key="x",
        database_url="postgres://db",
        supabase_url="http://example",
        supabase_service_role_key="key",
        data_dir=str(tmp_path),
    )
    dummy_queue = DummyQueue(enqueued=[])
    dummy_jobs = DummyJobsRepo(created=[], failed=[])

    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    monkeypatch.setattr("src.api.routes.split_pdf", lambda *_args, **_kwargs: [str(split_one), str(split_two)])
    monkeypatch.setattr("src.api.routes.SupabaseStorage", DummyStorage)
    monkeypatch.setattr("src.api.routes.SupabaseJobsRepository", lambda _db: dummy_jobs)
    monkeypatch.setattr(
        "src.api.routes.RedisQueue",
        type("RQ", (), {"from_settings": staticmethod(lambda _s: dummy_queue)}),
    )

    client = TestClient(app)
    resp = client.post(
        "/ingest",
        data={"client_id": "supply_chain"},
        files={"file": ("invoice.pdf", b"%PDF-1.4 root", "application/pdf")},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["job_ids"]) == 2
    assert len(dummy_jobs.created) == 2
    assert len(dummy_queue.enqueued) == 2
    assert {job["client_id"] for job in dummy_jobs.created} == {"supply_chain"}
    assert {job["client_id"] for job in dummy_queue.enqueued} == {"supply_chain"}
    assert {job["job_id"] for job in dummy_jobs.created} == set(body["job_ids"])


def test_ingest_rejects_unknown_client_id(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        llm_api_key="x",
        database_url="postgres://db",
        supabase_url="http://example",
        supabase_service_role_key="key",
        data_dir=str(tmp_path),
    )
    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)

    client = TestClient(app)
    resp = client.post(
        "/ingest",
        data={"client_id": "missing_client"},
        files={"file": ("invoice.pdf", b"%PDF-1.4 root", "application/pdf")},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Unknown client_id: missing_client"
