from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from src.core.graph import GraphDeps, _node_reconcile
from src.plugins.supply_chain import execute_3_way_match


def test_execute_3_way_match_includes_discrepancy_context_and_notification() -> None:
    invoice_data = {
        "line_items": [
            {
                "description": "Industrial Sensors",
                "quantity": 10,
                "unit_price": 12.0,
            }
        ]
    }
    po_lines = [
        {
            "item_description": "Industrial Sensors",
            "expected_unit_price": 12.0,
        }
    ]
    receipt_lines = [
        {
            "item_description": "Industrial Sensors",
            "actual_received_qty": 7,
        }
    ]

    audit = execute_3_way_match(invoice_data, po_lines, receipt_lines)

    assert audit["status"] == "BLOCKED_DISCREPANCY"
    assert audit["shortage_detected"] is True
    assert audit["notification"]["shortage_detected"] is True
    assert "shortage" in audit["notification"]["title"].lower()

    discrepancy = audit["discrepancies"][0]
    assert discrepancy["type"] == "QUANTITY_SHORTAGE"
    assert discrepancy["why"] == (
        "The invoice asks payment for more units than the warehouse confirmed as received."
    )
    assert discrepancy["where"]["field"] == "quantity"
    assert discrepancy["detected_from"]["sources"] == [
        "invoice.line_items.quantity",
        "erp_goods_receipts.actual_received_qty",
    ]
    assert discrepancy["anomaly"]["kind"] == "shortage"
    assert discrepancy["anomaly"]["expected"] == 7.0
    assert discrepancy["anomaly"]["actual"] == 10.0
    assert discrepancy["anomaly"]["delta"] == 3.0


def test_execute_3_way_match_blocks_when_line_items_are_missing() -> None:
    audit = execute_3_way_match(
        invoice_data={"invoice_number": "FA2109-0333"},
        po_lines=[{"item_description": "Pictogramme Adhésif A3.", "expected_unit_price": 11.67}],
        receipt_lines=[{"item_description": "Pictogramme Adhésif A3.", "actual_received_qty": 40}],
    )

    assert audit["status"] == "BLOCKED_DISCREPANCY"
    assert audit["notification"]["title"] == "Shortage could not be evaluated"
    discrepancy = audit["discrepancies"][0]
    assert discrepancy["type"] == "MISSING_LINE_ITEMS"
    assert discrepancy["where"]["field"] == "line_items"
    assert discrepancy["detected_from"]["comparison"] == "reconciliation_prerequisite_check"


@dataclass
class _Registry:
    async def get_po_lines(self, po_number: str) -> list[dict[str, Any]]:
        assert po_number in {"PO-7788", "CO2109-0171"}
        return [
            {
                "item_description": "Steel Bolts",
                "expected_unit_price": 4.5,
            }
        ]

    async def get_goods_receipts(self, po_number: str) -> list[dict[str, Any]]:
        assert po_number in {"PO-7788", "CO2109-0171"}
        return [
            {
                "item_description": "Steel Bolts",
                "actual_received_qty": 4,
            }
        ]


@dataclass
class _Jobs:
    completed_payloads: list[dict[str, Any]] = field(default_factory=list)

    async def mark_completed(
        self,
        job_id: str,
        vendor_detected: str | None,
        extracted_data: dict[str, Any],
    ) -> None:
        self.completed_payloads.append(extracted_data)


@dataclass
class _Webhook:
    async def send(self, job_id: str, payload: dict[str, Any]) -> None:
        return None


@pytest.mark.asyncio
async def test_reconcile_adds_processing_notification_to_completed_payload() -> None:
    jobs = _Jobs()
    deps = GraphDeps(registry=_Registry(), jobs=jobs, webhook=_Webhook())
    state = {
        "job_id": "job-1",
        "detected_vendor": "ACME",
        "final_output": {
            "order_reference": "PO-7788",
            "line_items": [
                {
                    "description": "Steel Bolts",
                    "quantity": 9,
                    "unit_price": 4.5,
                }
            ],
        },
    }

    command = await _node_reconcile(state, deps)

    assert command.goto == "deliver_webhook"
    payload = command.update["final_output"]
    notification = payload["processing_notification"]
    assert notification["shortage_detected"] is True
    assert "shortage" in notification["message"].lower()
    assert payload["audit_report"]["discrepancies"][0]["where"]["document"] == "invoice.line_items"
    assert jobs.completed_payloads[0]["processing_notification"]["shortage_detected"] is True


@pytest.mark.asyncio
async def test_reconcile_uses_purchase_order_number_alias() -> None:
    jobs = _Jobs()
    deps = GraphDeps(registry=_Registry(), jobs=jobs, webhook=_Webhook())
    state = {
        "job_id": "job-2",
        "detected_vendor": "LABEL_TECH",
        "final_output": {
            "purchase_order_number": "CO2109-0171",
            "line_items": [
                {
                    "description": "Steel Bolts",
                    "quantity": 4,
                    "unit_price": 4.5,
                }
            ],
        },
    }

    command = await _node_reconcile(state, deps)

    assert command.goto == "deliver_webhook"
    payload = command.update["final_output"]
    assert payload["audit_report"]["shortage_detected"] is False
    assert payload["processing_notification"]["shortage_detected"] is False
    assert payload["audit_report"]["status"] == "CLEARED_FOR_PAYMENT"
