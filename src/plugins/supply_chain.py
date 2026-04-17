"""
Supply Chain 3-Way Match Plugin.

Pure deterministic math — zero AI.
Compares: Invoice (extracted) vs Purchase Order vs Goods Receipt.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _normalize_description(value: Any) -> str:
    text = str(value or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _match_score(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        shorter = min(len(left), len(right))
        longer = max(len(left), len(right))
        return shorter / longer if longer else 0.0

    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0

    overlap = left_tokens & right_tokens
    if not overlap:
        return 0.0

    return len(overlap) / max(len(left_tokens), len(right_tokens))


def _find_best_match(description: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized_description = _normalize_description(description)
    best_match: dict[str, Any] | None = None
    best_score = 0.0

    for candidate in candidates:
        score = _match_score(
            normalized_description,
            _normalize_description(candidate.get("item_description")),
        )
        if score > best_score:
            best_score = score
            best_match = candidate

    return best_match if best_score >= 0.4 else None


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
        desc = str(inv_item.get("description", "") or "").strip()
        inv_qty = _coerce_float(inv_item.get("quantity"))
        inv_price = _coerce_float(inv_item.get("unit_price"))

        po_line = _find_best_match(desc, po_lines)
        receipt_line = _find_best_match(desc, receipt_lines)

        if not po_line:
            discrepancies.append({
                "type": "UNAUTHORIZED_ITEM",
                "item": desc,
                "message": "Item billed was not on the Purchase Order.",
            })
            continue

        # ── 2. Price match: Invoice vs Purchase Order ──
        expected_price = _coerce_float(po_line.get("expected_unit_price"))
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
        received_qty = _coerce_float(receipt_line.get("actual_received_qty") if receipt_line else 0.0)
        if inv_qty > received_qty:
            discrepancies.append({
                "type": "QUANTITY_SHORTAGE",
                "item": desc,
                "received": received_qty,
                "billed": inv_qty,
                "shortfall": round(inv_qty - received_qty, 2),
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
