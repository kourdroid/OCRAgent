from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src.api.app import app
from src.config import Settings


VALID_SCHEMA = {
    "vendor_name": "DHL_Express",
    "fields": [
        {
            "key": "invoice_number",
            "type": "str",
            "description": "Invoice identifier",
        }
    ],
    "version": 1,
}


@dataclass
class DummyQueue:
    enqueued: list[dict[str, Any]]

    async def enqueue_job(self, *, job_id: str, file_path: str, client_id: str = "default") -> str:
        self.enqueued.append({"job_id": job_id, "file_path": file_path, "client_id": client_id})
        return "1-0"

    async def close(self) -> None:
        return None


@dataclass
class DummyRegistryRepo:
    saved: list[dict[str, Any]]

    async def upsert_schema(
        self,
        vendor_name: str,
        fingerprint_hash: str,
        ocr_text_cache: str,
        schema_definition: dict[str, Any],
        client_id: str = "default",
    ) -> None:
        self.saved.append(
            {
                "client_id": client_id,
                "vendor_name": vendor_name,
                "fingerprint_hash": fingerprint_hash,
                "ocr_text_cache": ocr_text_cache,
                "schema_definition": schema_definition,
            }
        )


@dataclass
class DummyJobsRepo:
    job: dict[str, Any] | None
    requeued: list[tuple[str, str | None]]

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self.job

    async def mark_requeued(self, job_id: str, vendor_detected: str | None) -> None:
        self.requeued.append((job_id, vendor_detected))
        if self.job is not None:
            self.job["status"] = "PENDING"
            self.job["vendor_detected"] = vendor_detected

    async def get_file_url(self, job_id: str) -> str | None:
        return "file.pdf" if self.job else None


def _waiting_job(extracted_data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "job_id": "1",
        "client_id": "default",
        "status": "WAITING_HUMAN",
        "vendor_detected": "DHL_Express",
        "extracted_data": extracted_data
        if extracted_data is not None
        else {
            "fingerprint_hash": "abc123",
            "ocr_text_cache": "DHL invoice header",
        },
    }


def _client_with_repos(
    tmp_path: Path,
    monkeypatch,
    *,
    job: dict[str, Any] | None,
) -> tuple[TestClient, DummyQueue, DummyRegistryRepo, DummyJobsRepo]:
    settings = Settings(
        llm_api_key="x",
        database_url="postgres://db",
        supabase_url="http://example",
        supabase_service_role_key="key",
        data_dir=str(tmp_path),
    )
    dummy_queue = DummyQueue(enqueued=[])
    dummy_registry = DummyRegistryRepo(saved=[])
    dummy_jobs = DummyJobsRepo(job=job, requeued=[])

    monkeypatch.setattr("src.api.routes.get_settings", lambda: settings)
    monkeypatch.setattr("src.api.routes.SupabaseRegistryRepository", lambda _db: dummy_registry)
    monkeypatch.setattr("src.api.routes.SupabaseJobsRepository", lambda _db: dummy_jobs)
    monkeypatch.setattr(
        "src.api.routes.RedisQueue",
        type("RQ", (), {"from_settings": staticmethod(lambda _s: dummy_queue)}),
    )

    return TestClient(app), dummy_queue, dummy_registry, dummy_jobs


def test_approve_valid_waiting_human_job_persists_schema_and_requeues(tmp_path: Path, monkeypatch) -> None:
    client, dummy_queue, dummy_registry, dummy_jobs = _client_with_repos(
        tmp_path,
        monkeypatch,
        job=_waiting_job(),
    )

    resp = client.post(
        "/approve",
        json={"job_id": "1", "vendor_name": "DHL_Express", "schema_definition": VALID_SCHEMA},
    )

    assert resp.status_code == 200
    assert resp.json() == {"status": "queued", "job_id": "1"}
    assert dummy_registry.saved == [
        {
            "client_id": "default",
            "vendor_name": "DHL_Express",
            "fingerprint_hash": "abc123",
            "ocr_text_cache": "DHL invoice header",
            "schema_definition": VALID_SCHEMA,
        }
    ]
    assert dummy_jobs.requeued == [("1", "DHL_Express")]
    assert dummy_queue.enqueued == [{"job_id": "1", "file_path": "file.pdf", "client_id": "default"}]


def test_approve_rejects_invalid_schema_payload(tmp_path: Path, monkeypatch) -> None:
    client, _queue, _registry, _jobs = _client_with_repos(
        tmp_path,
        monkeypatch,
        job=_waiting_job(),
    )

    resp = client.post(
        "/approve",
        json={
            "job_id": "1",
            "vendor_name": "DHL_Express",
            "schema_definition": {"vendor_name": "DHL_Express", "fields": [{"key": "x", "type": "bad"}]},
        },
    )

    assert resp.status_code == 422


def test_approve_rejects_job_that_is_not_waiting_human(tmp_path: Path, monkeypatch) -> None:
    job = _waiting_job()
    job["status"] = "COMPLETED"
    client, dummy_queue, dummy_registry, dummy_jobs = _client_with_repos(tmp_path, monkeypatch, job=job)

    resp = client.post(
        "/approve",
        json={"job_id": "1", "vendor_name": "DHL_Express", "schema_definition": VALID_SCHEMA},
    )

    assert resp.status_code == 409
    assert dummy_registry.saved == []
    assert dummy_jobs.requeued == []
    assert dummy_queue.enqueued == []


def test_approve_rejects_missing_fingerprint_metadata(tmp_path: Path, monkeypatch) -> None:
    client, dummy_queue, dummy_registry, dummy_jobs = _client_with_repos(
        tmp_path,
        monkeypatch,
        job=_waiting_job({"proposed_schema": VALID_SCHEMA}),
    )

    resp = client.post(
        "/approve",
        json={"job_id": "1", "vendor_name": "DHL_Express", "schema_definition": VALID_SCHEMA},
    )

    assert resp.status_code == 409
    assert dummy_registry.saved == []
    assert dummy_jobs.requeued == []
    assert dummy_queue.enqueued == []


def test_approve_rejects_mismatched_client_id(tmp_path: Path, monkeypatch) -> None:
    job = _waiting_job()
    job["client_id"] = "supply_chain"
    client, dummy_queue, dummy_registry, dummy_jobs = _client_with_repos(
        tmp_path,
        monkeypatch,
        job=job,
    )

    resp = client.post(
        "/approve",
        json={"job_id": "1", "vendor_name": "DHL_Express", "schema_definition": VALID_SCHEMA},
    )

    assert resp.status_code == 409
    assert dummy_registry.saved == []
    assert dummy_jobs.requeued == []
    assert dummy_queue.enqueued == []


def test_approve_rejects_vendor_schema_mismatch(tmp_path: Path, monkeypatch) -> None:
    client, dummy_queue, dummy_registry, dummy_jobs = _client_with_repos(
        tmp_path,
        monkeypatch,
        job=_waiting_job(),
    )

    resp = client.post(
        "/approve",
        json={"job_id": "1", "vendor_name": "OtherVendor", "schema_definition": VALID_SCHEMA},
    )

    assert resp.status_code == 409
    assert dummy_registry.saved == []
    assert dummy_jobs.requeued == []
    assert dummy_queue.enqueued == []
