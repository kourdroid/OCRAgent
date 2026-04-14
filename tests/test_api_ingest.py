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

    async def close(self) -> None:
        return None


class DummyJobsRepo:
    async def create_job(self, *, job_id: str, file_url: str) -> None:
        return None


def test_ingest_creates_job_and_enqueues(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        google_api_key="x",
        supabase_url="http://example",
        supabase_service_role_key="key",
        data_dir=str(tmp_path),
    )

    dummy_queue = DummyQueue(enqueued=[])

    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    monkeypatch.setattr("src.api.routes.get_supabase_client", lambda _settings: object())
    monkeypatch.setattr("src.api.routes.SupabaseJobsRepository", lambda _client: DummyJobsRepo())
    monkeypatch.setattr("src.api.routes.RedisQueue", type("RQ", (), {"from_settings": staticmethod(lambda _s: dummy_queue)}))

    client = TestClient(app)
    resp = client.post("/ingest", files={"file": ("invoice.pdf", b"%PDF-1.4", "application/pdf")})
    assert resp.status_code == 200
    body = resp.json()
    assert "job_id" in body
    assert len(dummy_queue.enqueued) == 1

