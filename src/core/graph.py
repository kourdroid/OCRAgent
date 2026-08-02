from __future__ import annotations

import difflib
import functools
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import httpx
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.core.nodes import VendorIdentification, compute_fingerprint, discover_schema, extract_with_schema, identify_vendor
from src.core.state import AgentState
from src.plugins.supply_chain import execute_3_way_match
from src.schemas import RegistrySchema

logger = logging.getLogger(__name__)


_SANITIZE_PUNC_RE = re.compile(r'[\/:\-\.]+')
_SANITIZE_DIGIT_RE = re.compile(r'\d+')


# ⚡ Bolt Optimization:
# Memoize `_sanitize_for_match` to avoid redundant regex replacements
# and string operations during frequent iterations in `_node_fingerprint_and_lookup`.
# Improves processing speed significantly for repeated inputs.
@functools.lru_cache(maxsize=1024)
def _sanitize_for_match(text: str) -> str:
    if not text:
        return ""
    text = _SANITIZE_PUNC_RE.sub(' ', text)
    text = _SANITIZE_DIGIT_RE.sub('', text)
    return text.strip().lower()


_PO_NUMBER_RE = re.compile(r"[A-Za-z]{1,10}[A-Za-z0-9\-]*\d[A-Za-z0-9\-]*")


def _extract_po_number(value: Any) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""

    first_segment = raw_value.split("/", 1)[0].splitlines()[0].strip()
    match = _PO_NUMBER_RE.search(first_segment)
    return match.group(0).strip() if match else first_segment


def _find_po_reference(extracted_data: dict[str, Any]) -> tuple[str, str]:
    candidate_keys = [
        "order_reference",
        "po_number",
        "purchase_order_number",
        "purchase_order_no",
        "purchase_order_ref",
    ]

    for key in candidate_keys:
        raw_value = extracted_data.get(key, "")
        clean_value = _extract_po_number(raw_value)
        if clean_value:
            return key, clean_value

    return "", ""


def _build_processing_notification(audit_report: dict[str, Any]) -> dict[str, Any]:
    notification = audit_report.get("notification")
    if isinstance(notification, dict):
        return notification

    discrepancies = audit_report.get("discrepancies") or []
    shortage_detected = any(d.get("type") == "QUANTITY_SHORTAGE" for d in discrepancies)
    if shortage_detected:
        return {
            "shortage_detected": True,
            "severity": "warning",
            "title": "Quantity shortage detected",
            "message": "At least one invoice line exceeds the received quantity.",
        }

    if discrepancies:
        return {
            "shortage_detected": False,
            "severity": "warning",
            "title": "No quantity shortage detected",
            "message": "Document is blocked by a non-shortage discrepancy.",
        }

    return {
        "shortage_detected": False,
        "severity": "success",
        "title": "No quantity shortage detected",
        "message": "Document cleared with no shortage anomaly.",
    }


class RegistryRepository(Protocol):
    async def get_vendor_schemas(self, vendor_name: str) -> list[dict[str, Any]]: ...
    async def get_all_schemas(self) -> list[dict[str, Any]]: ...
    async def get_po_lines(self, po_number: str) -> list[dict[str, Any]]: ...
    async def get_goods_receipts(self, po_number: str) -> list[dict[str, Any]]: ...


class JobsRepository(Protocol):
    async def mark_processing(self, job_id: str, vendor_detected: Optional[str]) -> None: ...
    async def mark_waiting_human(self, job_id: str, vendor_detected: Optional[str], extracted_data: dict[str, Any]) -> None: ...
    async def mark_completed(self, job_id: str, vendor_detected: Optional[str], extracted_data: dict[str, Any]) -> None: ...
    async def mark_failed(self, job_id: str, error_log: str) -> None: ...


class WebhookClient(Protocol):
    async def send(self, job_id: str, payload: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class GraphDeps:
    registry: RegistryRepository
    jobs: JobsRepository
    webhook: WebhookClient


def _load_document(file_path: str) -> Any:
    if file_path.startswith("http://") or file_path.startswith("https://"):
        resp = httpx.get(file_path)
        resp.raise_for_status()
        pdf_bytes = resp.content
    else:
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()

    class PDFPart:
        mime_type = "application/pdf"
        data = pdf_bytes

    return PDFPart()


async def _node_fingerprint_and_lookup(state: AgentState, deps: GraphDeps) -> Command[str]:
    job_id = state.get("job_id")
    file_path = state.get("file_path")
    if not job_id or not file_path:
        return Command(update={"error": "Missing job_id or file_path"}, goto=END)

    logger.info("job=%s step=fingerprint_and_lookup status=start file=%s", job_id, file_path)
    await deps.jobs.mark_processing(job_id, None)

    image = _load_document(file_path)
    ident: VendorIdentification = await identify_vendor(image)

    fingerprint_hash = compute_fingerprint(ident.header_text)
    vendor_name = ident.vendor_name

    registry_rows = await deps.registry.get_all_schemas()

    best_match = None
    highest_ratio = 0.0

    sanitized_current = _sanitize_for_match(ident.header_text)

    # ⚡ Bolt Optimization:
    # Hoist SequenceMatcher initialization outside the loop to avoid redundant cache building for 'b'.
    # Use quick_ratio() to pre-filter candidates before calling the expensive ratio().
    matcher = difflib.SequenceMatcher(None, b=sanitized_current)

    for row in registry_rows:
        existing_text = row.get("ocr_text_cache") or ""
        sanitized_existing = _sanitize_for_match(existing_text)

        matcher.set_seq1(sanitized_existing)
        if matcher.quick_ratio() > highest_ratio:
            ratio = matcher.ratio()
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match = row

    if best_match and highest_ratio >= 0.80:
        matched_vendor = best_match.get("vendor_name") or vendor_name
        logger.info(
            "job=%s step=fingerprint_and_lookup registry=hit vendor=%s ratio=%.2f",
            job_id, matched_vendor, highest_ratio
        )
        return Command(
            update={
                "detected_vendor": matched_vendor,
                "current_schema": best_match["schema_definition"],
                "drift_confidence": highest_ratio,
                "fingerprint_hash": best_match.get("fingerprint_hash") or fingerprint_hash,
                "ocr_text_cache": ident.header_text,
            },
            goto="extract",
        )
    else:
        logger.info(
            "job=%s step=fingerprint_and_lookup registry=miss vendor=%s ratio=%.2f",
            job_id, vendor_name, highest_ratio
        )
        return Command(
            update={
                "detected_vendor": vendor_name,
                "fingerprint_hash": fingerprint_hash,
                "ocr_text_cache": ident.header_text,
                "drift_confidence": highest_ratio,
            },
            goto="discovery_agent",
        )


async def _node_discovery_agent(state: AgentState) -> Command[str]:
    job_id = state.get("job_id", "?")
    file_path = state.get("file_path")
    if not file_path:
        return Command(update={"error": "Missing file_path"}, goto=END)

    logger.info("job=%s step=discovery_agent status=start", job_id)
    image = _load_document(file_path)
    schema = await discover_schema(image)
    logger.info("job=%s step=discovery_agent status=done vendor=%s version=%s", job_id, schema.vendor_name, schema.version)
    return Command(update={"proposed_schema": schema.model_dump()}, goto="human_hold")


async def _node_human_hold(state: AgentState, deps: GraphDeps) -> Command[str]:
    job_id = state.get("job_id")
    proposed_schema = state.get("proposed_schema")
    vendor_name = state.get("detected_vendor")
    fingerprint_hash = state.get("fingerprint_hash")
    ocr_text_cache = state.get("ocr_text_cache")
    if not job_id or not proposed_schema:
        return Command(update={"error": "Missing job_id or proposed_schema"}, goto=END)

    logger.info("job=%s step=human_hold status=waiting vendor=%s", job_id, vendor_name)
    extracted_data = {
        "proposed_schema": proposed_schema,
        "fingerprint_hash": fingerprint_hash,
        "ocr_text_cache": ocr_text_cache,
    }
    await deps.jobs.mark_waiting_human(job_id, vendor_name, extracted_data)
    return Command(update={}, goto=END)


async def _node_extract(state: AgentState, deps: GraphDeps) -> Command[str]:
    job_id = state.get("job_id")
    file_path = state.get("file_path")
    vendor_name = state.get("detected_vendor")
    schema_dict = state.get("current_schema")
    if not job_id or not file_path or not schema_dict:
        return Command(update={"error": "Missing job_id, file_path, or current_schema"}, goto=END)

    logger.info("job=%s step=extract status=start vendor=%s", job_id, vendor_name)
    image = _load_document(file_path)
    schema = RegistrySchema.model_validate(schema_dict)
    extracted = await extract_with_schema(image, schema)

    await deps.jobs.mark_completed(job_id, vendor_name, extracted)
    logger.info("job=%s step=extract status=done keys=%s", job_id, sorted(list(extracted.keys())))
    return Command(update={"final_output": extracted}, goto="reconcile")


async def _node_reconcile(state: AgentState, deps: GraphDeps) -> Command[str]:
    job_id = state.get("job_id")
    extracted_data = state.get("final_output", {})
    vendor_name = state.get("detected_vendor")

    logger.info("job=%s step=reconcile status=start", job_id)

    po_source_key, clean_po = _find_po_reference(extracted_data)

    logger.info(
        "job=%s step=reconcile po_lookup source_key=%s available_keys=%s clean_po=%s",
        job_id,
        po_source_key or "missing",
        sorted(list(extracted_data.keys())),
        clean_po or "missing",
    )

    if not clean_po:
        logger.warning("job=%s step=reconcile status=blocked reason=no_po_found", job_id)
        audit = {
            "status": "BLOCKED_DISCREPANCY",
            "discrepancies": [
                {
                    "type": "UNAUTHORIZED_ITEM",
                    "item": "PO_REFERENCE",
                    "message": "No purchase order reference found in extracted invoice data.",
                    "why": "The document could not be linked to any ERP purchase order because no PO reference was extracted.",
                    "where": {
                        "document": "invoice.metadata",
                        "field": "order_reference|po_number|purchase_order_number",
                    },
                    "detected_from": {
                        "sources": [
                            "invoice.order_reference",
                            "invoice.po_number",
                            "invoice.purchase_order_number",
                        ],
                        "comparison": "po_reference_presence_check",
                    },
                    "anomaly": {
                        "kind": "missing_reference",
                        "metric": "purchase_order_reference",
                        "expected": "A valid PO number in the extracted invoice metadata",
                        "actual": "No PO-like value found in known PO reference fields",
                    },
                }
            ],
            "shortage_detected": False,
            "notification": {
                "shortage_detected": False,
                "severity": "warning",
                "title": "No quantity shortage detected",
                "message": "Document is blocked because no purchase order reference was found.",
                "discrepancy_count": 1,
            },
        }
        extracted_data["audit_report"] = audit
        extracted_data["processing_notification"] = _build_processing_notification(audit)
        if job_id:
            await deps.jobs.mark_completed(job_id, vendor_name, extracted_data)
        return Command(
            update={"final_output": extracted_data, "reconciliation_audit": audit},
            goto="deliver_webhook",
        )

    po_lines = await deps.registry.get_po_lines(clean_po)
    receipt_lines = await deps.registry.get_goods_receipts(clean_po)
    audit_report = execute_3_way_match(
        invoice_data=extracted_data,
        po_lines=po_lines,
        receipt_lines=receipt_lines,
        price_tolerance=0.05,
    )

    logger.info(
        "job=%s step=reconcile status=done audit_status=%s discrepancies=%d",
        job_id, audit_report["status"], len(audit_report["discrepancies"]),
    )

    extracted_data["audit_report"] = audit_report
    extracted_data["processing_notification"] = _build_processing_notification(audit_report)

    if job_id:
        await deps.jobs.mark_completed(job_id, vendor_name, extracted_data)

    return Command(
        update={"final_output": extracted_data, "reconciliation_audit": audit_report},
        goto="deliver_webhook",
    )


async def _node_deliver_webhook(state: AgentState, deps: GraphDeps) -> Command[str]:
    job_id = state.get("job_id")
    payload = state.get("final_output")
    if job_id and payload:
        logger.info("job=%s step=deliver_webhook status=start", job_id)
        await deps.webhook.send(job_id, payload)
        logger.info("job=%s step=deliver_webhook status=done", job_id)
    return Command(update={}, goto=END)


def build_graph(deps: GraphDeps, *, checkpointer: Any | None = None):
    builder = StateGraph(AgentState)

    async def fingerprint_and_lookup(state: AgentState) -> Command[str]:
        return await _node_fingerprint_and_lookup(state, deps)

    builder.add_node("discovery_agent", _node_discovery_agent)

    async def human_hold(state: AgentState) -> Command[str]:
        return await _node_human_hold(state, deps)

    async def extract(state: AgentState) -> Command[str]:
        return await _node_extract(state, deps)

    async def reconcile(state: AgentState) -> Command[str]:
        return await _node_reconcile(state, deps)

    async def deliver_webhook(state: AgentState) -> Command[str]:
        return await _node_deliver_webhook(state, deps)

    builder.add_node("fingerprint_and_lookup", fingerprint_and_lookup)
    builder.add_node("human_hold", human_hold)
    builder.add_node("extract", extract)
    builder.add_node("reconcile", reconcile)
    builder.add_node("deliver_webhook", deliver_webhook)

    builder.add_edge(START, "fingerprint_and_lookup")

    return builder.compile(checkpointer=checkpointer)
