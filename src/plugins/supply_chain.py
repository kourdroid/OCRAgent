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


def _match_score(
    left: str, left_tokens: set[str], right: str, right_tokens: set[str]
) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        shorter = min(len(left), len(right))
        longer = max(len(left), len(right))
        return shorter / longer if longer else 0.0

    if not left_tokens or not right_tokens:
        return 0.0

    overlap = left_tokens & right_tokens
    if not overlap:
        return 0.0

    return len(overlap) / max(len(left_tokens), len(right_tokens))


def _find_best_match(
    normalized_desc: str,
    desc_tokens: set[str],
    candidates: list[tuple[dict[str, Any], str, set[str]]]
) -> dict[str, Any] | None:
    best_match: dict[str, Any] | None = None
    best_score = 0.0

    for candidate, cand_norm, cand_tokens in candidates:
        score = _match_score(
            normalized_desc, desc_tokens, cand_norm, cand_tokens
        )
        if score > best_score:
            best_score = score
            best_match = candidate

    return best_match if best_score >= 0.4 else None


def _build_shortage_notification(
    discrepancies: list[dict[str, Any]]
) -> dict[str, Any]:
    shortage_items = [d for d in discrepancies if d.get("type") == "QUANTITY_SHORTAGE"]
    shortage_detected = bool(shortage_items)
    discrepancy_count = len(discrepancies)

    if shortage_detected:
        item_names = ", ".join(str(d.get("item") or "UNKNOWN_ITEM") for d in shortage_items[:3])
        extra_count = max(len(shortage_items) - 3, 0)
        suffix = f" (+{extra_count} more)" if extra_count else ""
        return {
            "shortage_detected": True,
            "severity": "warning",
            "title": "Quantity shortage detected",
            "message": f"Shortage found on {len(shortage_items)} item(s): {item_names}{suffix}.",
            "discrepancy_count": discrepancy_count,
        }

    if discrepancy_count:
        return {
            "shortage_detected": False,
            "severity": "warning",
            "title": "No quantity shortage detected",
            "message": f"Document is blocked by {discrepancy_count} non-shortage discrepancy(s).",
            "discrepancy_count": discrepancy_count,
        }

    return {
        "shortage_detected": False,
        "severity": "success",
        "title": "No quantity shortage detected",
        "message": "Document cleared with no shortage anomaly.",
        "discrepancy_count": 0,
    }


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
    invoice_items = invoice_data.get("line_items", [])
    if not isinstance(invoice_items, list):
        invoice_items = []

    if not invoice_items:
        discrepancies = [
            {
                "type": "MISSING_LINE_ITEMS",
                "item": "LINE_ITEMS",
                "message": "No invoice line items were extracted, so reconciliation could not be completed.",
                "why": "3-way matching requires extracted invoice line items before quantity and price checks can run.",
                "where": {
                    "document": "invoice.metadata",
                    "field": "line_items",
                    "item_description": "LINE_ITEMS",
                },
                "detected_from": {
                    "sources": [
                        "invoice.line_items",
                        "erp_po_lines",
                        "erp_goods_receipts",
                    ],
                    "comparison": "reconciliation_prerequisite_check",
                },
                "anomaly": {
                    "kind": "missing_input",
                    "metric": "invoice_line_items",
                    "expected": "One or more extracted invoice line items",
                    "actual": "No line items extracted from the invoice",
                },
            }
        ]
        return {
            "status": "BLOCKED_DISCREPANCY",
            "discrepancies": discrepancies,
            "shortage_detected": False,
            "notification": {
                "shortage_detected": False,
                "severity": "warning",
                "title": "Shortage could not be evaluated",
                "message": "Reconciliation is blocked because no invoice line items were extracted.",
                "discrepancy_count": 1,
            },
        }

    discrepancies: list[dict[str, Any]] = []

    # Precompute normalized descriptions and tokens for candidates
    # to avoid redundant O(N*M) string parsing
    po_candidates: list[tuple[dict[str, Any], str, set[str]]] = []
    for po in po_lines:
        norm = _normalize_description(po.get("item_description"))
        toks = set(norm.split()) if norm else set()
        po_candidates.append((po, norm, toks))

    rcpt_candidates: list[tuple[dict[str, Any], str, set[str]]] = []
    for rcpt in receipt_lines:
        norm = _normalize_description(rcpt.get("item_description"))
        toks = set(norm.split()) if norm else set()
        rcpt_candidates.append((rcpt, norm, toks))

    for inv_item in invoice_items:
        desc = str(inv_item.get("description", "") or "").strip()
        inv_qty = _coerce_float(inv_item.get("quantity"))
        inv_price = _coerce_float(inv_item.get("unit_price"))

        norm_desc = _normalize_description(desc)
        desc_toks = set(norm_desc.split()) if norm_desc else set()

        po_line = _find_best_match(norm_desc, desc_toks, po_candidates)
        receipt_line = _find_best_match(norm_desc, desc_toks, rcpt_candidates)

        if not po_line:
            discrepancies.append({
                "type": "UNAUTHORIZED_ITEM",
                "item": desc,
                "message": "Item billed was not on the Purchase Order.",
                "why": "The invoice line item could not be matched to any approved PO line.",
                "where": {
                    "document": "invoice.line_items",
                    "field": "description",
                    "item_description": desc,
                },
                "detected_from": {
                    "sources": [
                        "invoice.line_items.description",
                        "erp_po_lines.item_description",
                    ],
                    "comparison": "description_match",
                },
                "anomaly": {
                    "kind": "missing_reference",
                    "metric": "po_authorization",
                    "expected": "A matching PO line",
                    "actual": "No PO line matched this invoice item",
                },
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
                    "message": "Invoice unit price exceeds the configured tolerance against the PO line.",
                    "why": "The billed unit price differs from the approved purchase order price beyond tolerance.",
                    "where": {
                        "document": "invoice.line_items",
                        "field": "unit_price",
                        "item_description": desc,
                    },
                    "detected_from": {
                        "sources": [
                            "invoice.line_items.unit_price",
                            "erp_po_lines.expected_unit_price",
                        ],
                        "comparison": "price_tolerance_check",
                    },
                    "anomaly": {
                        "kind": "variance",
                        "metric": "unit_price",
                        "expected": expected_price,
                        "actual": inv_price,
                        "delta": round(inv_price - expected_price, 2),
                        "variance_pct": round((price_diff / expected_price) * 100, 2),
                    },
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
                "message": "Billed quantity is higher than the quantity received in goods receipt records.",
                "why": "The invoice asks payment for more units than the warehouse confirmed as received.",
                "where": {
                    "document": "invoice.line_items",
                    "field": "quantity",
                    "item_description": desc,
                },
                "detected_from": {
                    "sources": [
                        "invoice.line_items.quantity",
                        "erp_goods_receipts.actual_received_qty",
                    ],
                    "comparison": "received_quantity_check",
                },
                "anomaly": {
                    "kind": "shortage",
                    "metric": "quantity",
                    "expected": received_qty,
                    "actual": inv_qty,
                    "delta": round(inv_qty - received_qty, 2),
                },
            })

    status = "BLOCKED_DISCREPANCY" if discrepancies else "CLEARED_FOR_PAYMENT"
    shortage_detected = any(d.get("type") == "QUANTITY_SHORTAGE" for d in discrepancies)
    notification = _build_shortage_notification(discrepancies)

    logger.info(
        "step=3_way_match status=%s discrepancy_count=%d",
        status, len(discrepancies),
    )

    return {
        "status": status,
        "discrepancies": discrepancies,
        "shortage_detected": shortage_detected,
        "notification": notification,
    }
