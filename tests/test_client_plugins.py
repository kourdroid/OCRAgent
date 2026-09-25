from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from src.core.graph import GraphDeps, _node_reconcile
from src.plugins.base import ReconciliationRepos
from src.plugins.registry import ClientPluginRegistry
from src.schemas import RegistrySchema


@dataclass
class FakePlugin:
    client_id: str = "client_a"
    display_name: str = "Client A"
    calls: list[dict[str, Any]] = field(default_factory=list)

    def normalize_vendor_name(self, value: str) -> str:
        return value

    def enrich_schema(self, schema: RegistrySchema) -> RegistrySchema:
        return schema

    async def reconcile(
        self,
        extracted_data: dict[str, Any],
        repos: ReconciliationRepos,
    ) -> dict[str, Any]:
        self.calls.append(extracted_data)
        return {
            "status": "PLUGIN_OK",
            "discrepancies": [],
            "shortage_detected": False,
            "notification": {
                "shortage_detected": False,
                "severity": "success",
                "title": "Plugin OK",
                "message": "Plugin reconciliation ran.",
            },
            "plugin_id": self.client_id,
            "plugin_version": "test",
        }

    def build_delivery_payload(
        self,
        job_id: str,
        extracted_data: dict[str, Any],
    ) -> dict[str, Any]:
        return extracted_data


class DummyRegistry:
    async def get_po_lines(self, po_number: str) -> list[dict[str, Any]]:
        return []

    async def get_goods_receipts(self, po_number: str) -> list[dict[str, Any]]:
        return []


@dataclass
class DummyJobs:
    completed: list[dict[str, Any]] = field(default_factory=list)

    async def mark_completed(
        self,
        job_id: str,
        vendor_detected: str | None,
        extracted_data: dict[str, Any],
    ) -> None:
        self.completed.append(extracted_data)


class DummyWebhook:
    async def send(self, job_id: str, payload: dict[str, Any]) -> None:
        return None


@pytest.mark.asyncio
async def test_reconcile_delegates_to_selected_client_plugin() -> None:
    plugin = FakePlugin()
    deps = GraphDeps(
        registry=DummyRegistry(),
        jobs=DummyJobs(),
        webhook=DummyWebhook(),
        plugin_registry=ClientPluginRegistry({"client_a": plugin}),
    )

    command = await _node_reconcile(
        {
            "job_id": "job-1",
            "client_id": "client_a",
            "detected_vendor": "ACME",
            "final_output": {"invoice_number": "INV-1"},
        },
        deps,
    )

    assert command.goto == "deliver_webhook"
    assert len(plugin.calls) == 1
    assert plugin.calls[0]["invoice_number"] == "INV-1"
    assert command.update["reconciliation_audit"]["plugin_id"] == "client_a"
