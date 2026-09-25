from __future__ import annotations

import io
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from src.api.app import app
from src.api.auth import require_super_admin
from src.api.dossier_routes import _reprocess_with_deadlock_retry
from src.config import Settings


def _pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class _Storage:
    uploaded: list[str] = []
    deleted: list[str] = []

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    async def upload(self, path: str, _data: bytes) -> str:
        self.uploaded.append(path)
        return f"https://storage.example/{path}"

    async def delete(self, paths: list[str]) -> None:
        self.deleted.extend(paths)


class _Repository:
    created: dict[str, Any] | None = None
    parties: list[dict[str, Any]] = []

    def __init__(self, _database_url: str) -> None:
        pass

    async def list_parties(self, **_kwargs: Any) -> list[dict[str, Any]]:
        return self.parties

    async def create_case_with_sources(self, **kwargs: Any) -> dict[str, Any]:
        self.created = kwargs
        sources = kwargs["sources"]
        return {
            "case_id": kwargs["case_id"],
            "document_ids": [source["document_id"] for source in sources],
            "job_ids": [source["job_id"] for source in sources],
            "status": "INGESTED",
        }


@pytest.fixture(autouse=True)
def authenticated_super_admin() -> None:
    app.dependency_overrides[require_super_admin] = lambda: {"id": "00000000-0000-0000-0000-000000000001"}
    yield
    app.dependency_overrides.pop(require_super_admin, None)


def test_dossier_ingest_keeps_multiple_files_in_one_case(monkeypatch) -> None:
    settings = Settings(
        llm_api_key="test",
        database_url="postgres://db",
        supabase_url="https://supabase.example",
        supabase_service_role_key="service-role",
    )
    repository = _Repository(settings.database_url)
    _Storage.uploaded = []
    _Storage.deleted = []

    monkeypatch.setattr("src.api.dossier_routes.get_settings", lambda: settings)
    monkeypatch.setattr("src.api.dossier_routes.SupabaseStorage", _Storage)
    monkeypatch.setattr(
        "src.api.dossier_routes.DossierRepository",
        lambda _database_url: repository,
    )

    client = TestClient(app)
    response = client.post(
        "/dossiers",
        data={
            "client_id": "delassus",
            "external_reference": "SHIP-2026-001",
        },
        files=[
            ("files", ("BL.pdf", _pdf_bytes(), "application/pdf")),
            ("files", ("BAD.pdf", _pdf_bytes(), "application/pdf")),
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "INGESTED"
    assert len(payload["document_ids"]) == 2
    assert len(payload["job_ids"]) == 2
    assert repository.created is not None
    assert repository.created["client_id"] == "delassus"
    assert repository.created["external_reference"] == "SHIP-2026-001"
    assert repository.created["workflow_id"] == "morocco_import_dossier"
    assert repository.created["intake"]["intake_channel"] == "WEB_UPLOAD"
    assert len({source["sha256"] for source in repository.created["sources"]}) == 1


def test_dossier_ingest_persists_sender_and_per_file_issuer(monkeypatch) -> None:
    settings = Settings(
        llm_api_key="test",
        database_url="postgres://db",
        supabase_url="https://supabase.example",
        supabase_service_role_key="service-role",
    )
    sender_id = "00000000-0000-0000-0000-000000000010"
    issuer_id = "00000000-0000-0000-0000-000000000011"
    repository = _Repository(settings.database_url)
    repository.parties = [{"party_id": sender_id}, {"party_id": issuer_id}]
    _Storage.uploaded = []

    monkeypatch.setattr("src.api.dossier_routes.get_settings", lambda: settings)
    monkeypatch.setattr("src.api.dossier_routes.SupabaseStorage", _Storage)
    monkeypatch.setattr("src.api.dossier_routes.DossierRepository", lambda _url: repository)

    response = TestClient(app).post(
        "/dossiers",
        data={
            "client_id": "delassus",
            "sender_party_id": sender_id,
            "issuer_manifest_json": f'{{"BL.pdf":"{issuer_id}"}}',
        },
        files=[("files", ("BL.pdf", _pdf_bytes(), "application/pdf"))],
    )

    assert response.status_code == 200
    assert repository.created is not None
    assert repository.created["intake"]["sender_party_id"] == sender_id
    assert repository.created["sources"][0]["issuer_party_id"] == issuer_id
    assert repository.created["sources"][0]["provenance_status"] == "COMPLETE"


def test_dossier_ingest_rejects_unknown_client(monkeypatch) -> None:
    settings = Settings(
        llm_api_key="test",
        database_url="postgres://db",
        supabase_url="https://supabase.example",
        supabase_service_role_key="service-role",
    )
    monkeypatch.setattr("src.api.dossier_routes.get_settings", lambda: settings)

    response = TestClient(app).post(
        "/dossiers",
        data={"client_id": "unknown"},
        files=[("files", ("BL.pdf", _pdf_bytes(), "application/pdf"))],
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown client_id: unknown"


def test_dossier_routes_require_authentication() -> None:
    app.dependency_overrides.pop(require_super_admin, None)
    response = TestClient(app).get("/dossiers?client_id=delassus")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication is required"


@pytest.mark.parametrize(
    "path",
    [
        "/dossiers/not-a-uuid?client_id=delassus",
        "/dossiers/not-a-uuid/report?client_id=delassus&format=json",
    ],
)
def test_dossier_routes_hide_malformed_case_ids(path: str) -> None:
    response = TestClient(app).get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == "Dossier not found"


@pytest.mark.asyncio
async def test_reprocess_retries_database_deadlock(monkeypatch) -> None:
    class _DeadlockingRepository:
        calls = 0

        async def reprocess_sources(self, **_kwargs: Any) -> list[str]:
            self.calls += 1
            if self.calls < 3:
                import asyncpg

                raise asyncpg.DeadlockDetectedError("deadlock")
            return ["job-1"]

    async def no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr("src.api.dossier_routes.asyncio.sleep", no_sleep)
    repository = _DeadlockingRepository()

    job_ids = await _reprocess_with_deadlock_retry(
        repository,  # type: ignore[arg-type]
        case_id="case-1",
        client_id="delassus",
        document_ids=["document-1"],
        reason="retry",
    )

    assert job_ids == ["job-1"]
    assert repository.calls == 3
