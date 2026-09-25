from __future__ import annotations

from typing import Any, Protocol

from src.dossiers.models import DossierCaseContext, DossierDecision, DocumentType
from src.schemas import RegistrySchema


DEFAULT_CLIENT_ID = "default"


class ReconciliationRepos(Protocol):
    async def get_po_lines(
        self,
        po_number: str,
        client_id: str = DEFAULT_CLIENT_ID,
    ) -> list[dict[str, Any]]: ...

    async def get_goods_receipts(
        self,
        po_number: str,
        client_id: str = DEFAULT_CLIENT_ID,
    ) -> list[dict[str, Any]]: ...


class ClientPlugin(Protocol):
    client_id: str
    display_name: str

    def normalize_vendor_name(self, value: str) -> str: ...

    def enrich_schema(self, schema: RegistrySchema) -> RegistrySchema: ...

    async def reconcile(
        self,
        extracted_data: dict[str, Any],
        repos: ReconciliationRepos,
    ) -> dict[str, Any]: ...

    def build_delivery_payload(
        self,
        job_id: str,
        extracted_data: dict[str, Any],
    ) -> dict[str, Any]: ...


class WorkflowPlugin(Protocol):
    workflow_id: str
    workflow_version: str
    supported_document_types: frozenset[DocumentType]

    def validate_document_types(
        self,
        document_types: list[DocumentType],
    ) -> list[str]: ...

    def schema_for(self, document_type: DocumentType) -> tuple[str, ...]: ...

    def reconcile(self, case_context: DossierCaseContext) -> DossierDecision: ...

    def build_report(
        self,
        case_context: DossierCaseContext,
        decision: DossierDecision,
    ) -> dict[str, Any]: ...
