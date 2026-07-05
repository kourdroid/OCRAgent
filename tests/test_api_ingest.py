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

    async def enqueue_job(self, *, job_id: str, file_path: str) -> str:
        self.enqueued.append({"job_id": job_id, "file_path": file_path})
        return "1-0"

    async def enqueue_jobs_bulk(self, jobs_data: list[dict[str, Any]]) -> list[str]:
        for job in jobs_data:
            self.enqueued.append({"job_id": job["job_id"], "file_path": job["file_path"]})
        return [f"1-{i}" for i in range(len(jobs_data))]

    async def close(self) -> None:
        return None


class DummyJobsRepo:
    async def create_job(self, *, job_id: str, file_url: str) -> None:
        return None

    async def create_jobs_bulk(self, jobs_data: list[dict[str, Any]]) -> None:
        return None

class DummyStorage:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def upload(self, path: str, data: bytes, content_type: str = "application/pdf") -> str:
        return "http://example.com/file.pdf"


def test_ingest_creates_job_and_enqueues(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        google_api_key="x",
        database_url="postgres://db",
        supabase_url="http://example",
        supabase_service_role_key="key",
        data_dir=str(tmp_path),
    )

    dummy_queue = DummyQueue(enqueued=[])

    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    monkeypatch.setattr("src.api.routes.SupabaseStorage", DummyStorage)
    monkeypatch.setattr("src.api.routes.split_pdf", lambda *_args, **_kwargs: [str(tmp_path / "x.pdf")])
    monkeypatch.setattr("src.api.routes.SupabaseJobsRepository", lambda _client: DummyJobsRepo())
    monkeypatch.setattr("src.api.routes.RedisQueue", type("RQ", (), {"from_settings": staticmethod(lambda _s: dummy_queue)}))

    Path(tmp_path / "x.pdf").write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<\n/Size 2\n/Root 1 0 R\n>>\nstartxref\n50\n%%EOF\n")

    client = TestClient(app)
    resp = client.post("/ingest", files={"file": ("invoice.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<\n/Size 2\n/Root 1 0 R\n>>\nstartxref\n50\n%%EOF\n", "application/pdf")})
    assert resp.status_code == 200
    body = resp.json()
    assert "job_ids" in body
    assert len(dummy_queue.enqueued) == 1

