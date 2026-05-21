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

    async def mark_failed(self, job_id: str, error_log: str) -> None:
        return None


class FailingStorage:
    def __init__(self, *_args, **_kwargs) -> None:
        return None

    async def upload(self, path: str, data: bytes, content_type: str = "application/pdf") -> str:
        raise TimeoutError("storage upload timed out")


def test_ingest_returns_split_phase_failure_detail(tmp_path: Path, monkeypatch) -> None:
    split_pdf_path = tmp_path / "split_001.pdf"
    split_pdf_path.write_bytes(b"%PDF-1.4 split")

    settings = Settings(
        llm_api_key="x",
        database_url="postgres://db",
        supabase_url="http://example",
        supabase_service_role_key="key",
        data_dir=str(tmp_path),
    )

    dummy_queue = DummyQueue(enqueued=[])

    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    monkeypatch.setattr("src.api.routes.split_pdf", lambda *_args, **_kwargs: [str(split_pdf_path)])
    monkeypatch.setattr("src.api.routes.SupabaseStorage", FailingStorage)
    monkeypatch.setattr("src.api.routes.SupabaseJobsRepository", lambda _db: DummyJobsRepo())
    monkeypatch.setattr(
        "src.api.routes.RedisQueue",
        type("RQ", (), {"from_settings": staticmethod(lambda _s: dummy_queue)}),
    )

    client = TestClient(app)
    resp = client.post("/ingest", files={"file": ("invoice.pdf", b"%PDF-1.4 root", "application/pdf")})

    assert resp.status_code == 500
    assert "during upload" in resp.json()["detail"]
    assert "multiple_splits" in resp.json()["detail"]

