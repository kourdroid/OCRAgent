from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol

from typing import Any, Optional, Protocol

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.config import get_settings
from src.core.nodes import VendorIdentification, discover_schema, extract_with_schema, identify_vendor
from src.core.state import AgentState
from src.schemas import RegistrySchema

logger = logging.getLogger(__name__)


class RegistryRepository(Protocol):
    async def get_vendor_schemas(self, vendor_name: str) -> list[dict[str, Any]]: ...


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
    # Stop using pdf2image. Read the raw bytes.
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
    
    # Return a Gemini Part object for the PDF
    from google.genai import types
    return types.Part.from_bytes(
        data=pdf_bytes,
        mime_type="application/pdf",
    )


async def _node_fingerprint_and_lookup(state: AgentState, deps: GraphDeps) -> Command[str]:
    job_id = state.get("job_id")
    file_path = state.get("file_path")
    if not job_id or not file_path:
        return Command(update={"error": "Missing job_id or file_path"}, goto=END)

    logger.info("job=%s step=fingerprint_and_lookup status=start file=%s", job_id, file_path)
    await deps.jobs.mark_processing(job_id, None)

    import difflib
    image = _load_document(file_path)
    ident: VendorIdentification = await identify_vendor(image)

    from src.core.nodes import compute_fingerprint

    fingerprint_hash = compute_fingerprint(ident.header_text)
    vendor_name = ident.vendor_name

    # Fetch ALL registered schemas for this vendor
    registry_rows = await deps.registry.get_vendor_schemas(vendor_name)
    
    best_match = None
    highest_ratio = 0.0
    
    for row in registry_rows:
        existing_text = row.get("ocr_text_cache", "")
        # Use fuzzy string matching to check if the header is 85%+ similar
        ratio = difflib.SequenceMatcher(None, ident.header_text, existing_text).ratio()
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = row

    if best_match and highest_ratio >= 0.85:
        # It's the same layout (allow for minor OCR typos/date changes)
        logger.info(
            "job=%s step=fingerprint_and_lookup registry=hit vendor=%s ratio=%.2f",
            job_id, vendor_name, highest_ratio
        )
        return Command(
            update={
                "detected_vendor": vendor_name,
                "current_schema": best_match["schema_definition"],
                "drift_confidence": highest_ratio,
                "fingerprint_hash": best_match.get("fingerprint_hash") or fingerprint_hash,
                "ocr_text_cache": ident.header_text,
            },
            goto="extract",
        )
    else:
        # Truly a new layout (Ratio < 0.85)
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


async def _node_schema_evolution_agent(state: AgentState) -> Command[str]:
    job_id = state.get("job_id", "?")
    file_path = state.get("file_path")
    if not file_path:
        return Command(update={"error": "Missing file_path"}, goto=END)

    logger.info("job=%s step=schema_evolution_agent status=start", job_id)
    image = _load_document(file_path)
    schema = await discover_schema(image)

    vendor_name = state.get("detected_vendor")
    current_schema_dict = state.get("current_schema") or {}
    try:
        current_schema = RegistrySchema.model_validate(current_schema_dict)
        schema = schema.model_copy(update={"vendor_name": vendor_name or schema.vendor_name, "version": current_schema.version + 1})
    except Exception:
        schema = schema.model_copy(update={"vendor_name": vendor_name or schema.vendor_name})

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
    return Command(update={"final_output": extracted}, goto="deliver_webhook")


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
    builder.add_node("schema_evolution_agent", _node_schema_evolution_agent)

    async def human_hold(state: AgentState) -> Command[str]:
        return await _node_human_hold(state, deps)

    async def extract(state: AgentState) -> Command[str]:
        return await _node_extract(state, deps)

    async def deliver_webhook(state: AgentState) -> Command[str]:
        return await _node_deliver_webhook(state, deps)

    builder.add_node("fingerprint_and_lookup", fingerprint_and_lookup)
    builder.add_node("human_hold", human_hold)
    builder.add_node("extract", extract)
    builder.add_node("deliver_webhook", deliver_webhook)

    builder.add_edge(START, "fingerprint_and_lookup")

    return builder.compile(checkpointer=checkpointer)
