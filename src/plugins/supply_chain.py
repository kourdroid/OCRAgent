"""
Supply Chain 3-Way Match Plugin.

Pure deterministic math — zero AI.
Compares: Invoice (extracted) vs Purchase Order vs Goods Receipt.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def execute_3_way_match(
    invoice_data: dict[str, Any],
    po_lines: list[dict[str, Any]],
    receipt_lines: list[dict[str, Any]],
    price_tolerance: float = 0.05,
) -> dict[str, Any]:
    """
    Deterministic 3-Way Match engine.

    Args:
        invoice_data: Extracted invoice JSON (must contain "line_items").
        po_lines: Rows from erp_po_lines for the matched PO.
        receipt_lines: Rows from erp_goods_receipts for the matched PO.
        price_tolerance: Fractional tolerance for unit price variance (0.05 = 5%).

    Returns:
        {"status": "CLEARED_FOR_PAYMENT" | "BLOCKED_DISCREPANCY",
         "discrepancies": [...]}
    """
    discrepancies: list[dict[str, Any]] = []

    for inv_item in invoice_data.get("line_items", []):
        desc = inv_item.get("description", "")
        inv_qty = float(inv_item.get("quantity", 0))
        inv_price = float(inv_item.get("unit_price", 0))

        # ── 1. Map to PO line (substring match for MVP) ──
        po_line = next(
            (po for po in po_lines if po["item_description"] in desc or desc in po["item_description"]),
            None,
        )
        receipt_line = next(
            (gr for gr in receipt_lines if gr["item_description"] in desc or desc in gr["item_description"]),
            None,
        )

        if not po_line:
            discrepancies.append({
                "type": "UNAUTHORIZED_ITEM",
                "item": desc,
                "message": "Item billed was not on the Purchase Order.",
            })
            continue

        # ── 2. Price match: Invoice vs Purchase Order ──
        expected_price = float(po_line["expected_unit_price"])
        if expected_price > 0:
            price_diff = abs(inv_price - expected_price)
            if (price_diff / expected_price) > price_tolerance:
                discrepancies.append({
                    "type": "PRICE_VARIANCE",
                    "item": desc,
                    "expected": expected_price,
                    "billed": inv_price,
                    "variance_pct": round((price_diff / expected_price) * 100, 2),
                })

        # ── 3. Quantity match: Invoice vs Goods Receipt ──
        if not receipt_line:
            discrepancies.append({
                "type": "MISSING_RECEIPT",
                "item": desc,
                "message": "Item billed, but never received by warehouse.",
            })
        else:
            received_qty = float(receipt_line["actual_received_qty"])
            if inv_qty > received_qty:
                discrepancies.append({
                    "type": "QUANTITY_SHORTAGE",
                    "item": desc,
                    "received": received_qty,
                    "billed": inv_qty,
                    "over_billed": round(inv_qty - received_qty, 2),
                })

    status = "BLOCKED_DISCREPANCY" if discrepancies else "CLEARED_FOR_PAYMENT"

    logger.info(
        "step=3_way_match status=%s discrepancy_count=%d",
        status, len(discrepancies),
    )

    return {
        "status": status,
        "discrepancies": discrepancies,
    }
