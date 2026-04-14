from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from src.core.graph import GraphDeps, build_graph
from src.core.nodes import VendorIdentification
from src.schemas import RegistrySchema


@dataclass
class DummyRegistry:
    async def get_vendor(self, vendor_name: str) -> Optional[dict[str, Any]]:
        return None


@dataclass
class DummyJobs:
    called: list[str]

    async def mark_processing(self, job_id: str, vendor_detected: Optional[str]) -> None:
        self.called.append("processing")

    async def mark_waiting_human(self, job_id: str, vendor_detected: Optional[str], proposed_schema: dict[str, Any]) -> None:
        self.called.append("waiting_human")

    async def mark_completed(self, job_id: str, vendor_detected: Optional[str], extracted_data: dict[str, Any]) -> None:
        self.called.append("completed")

    async def mark_failed(self, job_id: str, error_log: str) -> None:
        self.called.append("failed")


@dataclass
class DummyWebhook:
    async def send(self, job_id: str, payload: dict[str, Any]) -> None:
        return None


@pytest.mark.asyncio
async def test_graph_nodes_are_awaited(monkeypatch) -> None:
    async def fake_identify_vendor(_image) -> VendorIdentification:
        return VendorIdentification(vendor_name="DHL_Express", header_text="HEADER")

    async def fake_discover_schema(_image):
        return RegistrySchema(vendor_name="DHL_Express", fields=[], version=1)

    monkeypatch.setattr("src.core.graph._load_first_page_image", lambda _p: object())
    monkeypatch.setattr("src.core.graph.identify_vendor", fake_identify_vendor)
    monkeypatch.setattr("src.core.graph.discover_schema", fake_discover_schema)

    jobs = DummyJobs(called=[])
    deps = GraphDeps(registry=DummyRegistry(), jobs=jobs, webhook=DummyWebhook())
    graph = build_graph(deps, checkpointer=InMemorySaver())

    await graph.ainvoke({"job_id": "1", "file_path": "x.pdf"}, {"configurable": {"thread_id": "1"}})

    assert "processing" in jobs.called
    assert "waiting_human" in jobs.called
