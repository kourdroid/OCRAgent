from __future__ import annotations

import difflib
import functools
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import aiofiles
import httpx
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.core.nodes import VendorIdentification, compute_fingerprint, discover_schema, extract_with_schema, identify_vendor
from src.core.state import AgentState
from src.plugins.base import DEFAULT_CLIENT_ID
from src.plugins.registry import ClientPluginRegistry, DEFAULT_PLUGIN_REGISTRY
from src.schemas import RegistrySchema

logger = logging.getLogger(__name__)


_SANITIZE_PUNC_RE = re.compile(r'[\/:\-\.]+')
_SANITIZE_DIGIT_RE = re.compile(r'\d+')


# ⚡ Bolt Optimization: Cache text sanitization since registry rows are processed multiple times
@functools.lru_cache(maxsize=1024)
def _sanitize_for_match(text: str) -> str:
    if not text:
        return ""
    text = _SANITIZE_PUNC_RE.sub(' ', text)
    text = _SANITIZE_DIGIT_RE.sub('', text)
    return text.strip().lower()


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
    async def get_vendor_schemas(
        self,
        vendor_name: str,
        client_id: str = DEFAULT_CLIENT_ID,
    ) -> list[dict[str, Any]]: ...

    async def get_all_schemas(
        self,
        client_id: str = DEFAULT_CLIENT_ID,
    ) -> list[dict[str, Any]]: ...

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
    plugin_registry: ClientPluginRegistry = DEFAULT_PLUGIN_REGISTRY
    drift_threshold: float = 0.8


async def _load_document(file_path: str) -> Any:
    if file_path.startswith("http://") or file_path.startswith("https://"):
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(file_path)
            response.raise_for_status()
            pdf_bytes = response.content
    else:
        async with aiofiles.open(file_path, "rb") as file:
            pdf_bytes = await file.read()

    class PDFPart:
        mime_type = "application/pdf"
        data = pdf_bytes

    return PDFPart()


async def _node_fingerprint_and_lookup(state: AgentState, deps: GraphDeps) -> Command[str]:
    job_id = state.get("job_id")
    file_path = state.get("file_path")
    client_id = state.get("client_id") or DEFAULT_CLIENT_ID
    if not job_id or not file_path:
        return Command(update={"error": "Missing job_id or file_path"}, goto=END)

    plugin = deps.plugin_registry.get(client_id)

    logger.info(
        "job=%s client=%s step=fingerprint_and_lookup status=start file=%s",
        job_id,
        client_id,
        file_path,
    )
    await deps.jobs.mark_processing(job_id, None)

    image = await _load_document(file_path)
    ident: VendorIdentification = await identify_vendor(image)

    fingerprint_hash = compute_fingerprint(ident.header_text)
    vendor_name = plugin.normalize_vendor_name(ident.vendor_name)

    registry_rows = await deps.registry.get_all_schemas(client_id=client_id)

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

    if best_match and highest_ratio >= deps.drift_threshold:
        matched_vendor = best_match.get("vendor_name") or vendor_name
        logger.info(
            "job=%s step=fingerprint_and_lookup registry=hit vendor=%s ratio=%.2f",
            job_id, matched_vendor, highest_ratio
        )
        return Command(
            update={
                "client_id": client_id,
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
                "client_id": client_id,
                "detected_vendor": vendor_name,
                "fingerprint_hash": fingerprint_hash,
                "ocr_text_cache": ident.header_text,
                "drift_confidence": highest_ratio,
            },
            goto="discovery_agent",
        )


async def _node_discovery_agent(state: AgentState, deps: GraphDeps) -> Command[str]:
    job_id = state.get("job_id", "?")
    file_path = state.get("file_path")
    client_id = state.get("client_id") or DEFAULT_CLIENT_ID
    if not file_path:
        return Command(update={"error": "Missing file_path"}, goto=END)

    plugin = deps.plugin_registry.get(client_id)
    logger.info("job=%s step=discovery_agent status=start", job_id)
    image = await _load_document(file_path)
    schema = plugin.enrich_schema(await discover_schema(image))
    logger.info("job=%s step=discovery_agent status=done vendor=%s version=%s", job_id, schema.vendor_name, schema.version)
    return Command(
        update={"client_id": client_id, "proposed_schema": schema.model_dump()},
        goto="human_hold",
    )


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
    image = await _load_document(file_path)
    schema = RegistrySchema.model_validate(schema_dict)
    extracted = await extract_with_schema(image, schema)

    logger.info("job=%s step=extract status=done keys=%s", job_id, sorted(list(extracted.keys())))
    return Command(update={"final_output": extracted}, goto="reconcile")


async def _node_reconcile(state: AgentState, deps: GraphDeps) -> Command[str]:
    job_id = state.get("job_id")
    extracted_data = state.get("final_output", {})
    vendor_name = state.get("detected_vendor")
    client_id = state.get("client_id") or DEFAULT_CLIENT_ID

    logger.info("job=%s client=%s step=reconcile status=start", job_id, client_id)
    plugin = deps.plugin_registry.get(client_id)
    audit_report = await plugin.reconcile(extracted_data, deps.registry)

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
    client_id = state.get("client_id") or DEFAULT_CLIENT_ID
    payload = state.get("final_output")
    if job_id and payload:
        plugin = deps.plugin_registry.get(client_id)
        delivery_payload = plugin.build_delivery_payload(job_id, payload)
        logger.info("job=%s client=%s step=deliver_webhook status=start", job_id, client_id)
        await deps.webhook.send(job_id, delivery_payload)
        logger.info("job=%s step=deliver_webhook status=done", job_id)
    return Command(update={}, goto=END)


def build_graph(deps: GraphDeps, *, checkpointer: Any | None = None):
    builder = StateGraph(AgentState)

    async def fingerprint_and_lookup(state: AgentState) -> Command[str]:
        return await _node_fingerprint_and_lookup(state, deps)

    async def discovery_agent(state: AgentState) -> Command[str]:
        return await _node_discovery_agent(state, deps)

    builder.add_node("discovery_agent", discovery_agent)

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
