from __future__ import annotations

import copy
import hashlib
import logging
from typing import Any

from pydantic import BaseModel, Field, create_model

from src.config import Settings, get_settings
from src.infrastructure.openai_provider import OpenAICompatibleDocumentProvider
from src.schemas import FieldDefinition
from src.schemas import LineItem, RegistrySchema

logger = logging.getLogger(__name__)


class VendorIdentification(BaseModel):
    vendor_name: str = Field(min_length=1)
    header_text: str = Field(min_length=1)


def compute_fingerprint(text: str) -> str:
    normalized = " ".join(text.split()).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


_UNSUPPORTED_SCHEMA_KEYS = {
    "default",
    "title",
    "minLength",
    "maxLength",
    "pattern",
    "format",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minItems",
    "maxItems",
    "minProperties",
    "maxProperties",
    "$defs",
    "$ref",
}


def _strip_schema_defaults(obj: Any) -> None:
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if key in _UNSUPPORTED_SCHEMA_KEYS:
                obj.pop(key, None)
        for value in obj.values():
            _strip_schema_defaults(value)
        return
    if isinstance(obj, list):
        for item in obj:
            _strip_schema_defaults(item)


def _inline_refs(obj: Any, defs: dict[str, Any], stack: set[str]) -> Any:
    if isinstance(obj, list):
        return [_inline_refs(v, defs, stack) for v in obj]
    if not isinstance(obj, dict):
        return obj

    if "$ref" in obj:
        ref = obj.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            key = ref.split("#/$defs/", 1)[1]
            if key in stack:
                return {k: _inline_refs(v, defs, stack) for k, v in obj.items() if k != "$ref"}
            resolved = copy.deepcopy(defs.get(key, {}))
            merged = {**resolved, **{k: v for k, v in obj.items() if k != "$ref"}}
            return _inline_refs(merged, defs, {*(stack), key})

    return {k: _inline_refs(v, defs, stack) for k, v in obj.items()}


def get_clean_schema(pydantic_model: type[BaseModel]) -> dict[str, Any]:
    schema = pydantic_model.model_json_schema()
    defs: Any = None
    if isinstance(schema, dict):
        defs = schema.pop("$defs", None) or schema.pop("definitions", None)
    if isinstance(defs, dict):
        schema = _inline_refs(schema, defs, set())
    _strip_schema_defaults(schema)
    return schema


def _ensure_required_invoice_fields(schema: RegistrySchema) -> RegistrySchema:
    field_map = {field.key: field for field in schema.fields}
    invoice_markers = {
        "invoice_number",
        "invoice_date",
        "due_date",
        "total_amount",
        "subtotal_amount",
        "tax_amount",
        "currency",
    }
    is_invoice_like = any(key in field_map for key in invoice_markers)
    if not is_invoice_like:
        return schema

    updated_fields = list(schema.fields)
    added_keys: list[str] = []

    if "purchase_order_number" not in field_map:
        updated_fields.append(
            FieldDefinition(
                key="purchase_order_number",
                type="str",
                description="Purchase order reference associated with this invoice.",
            )
        )
        added_keys.append("purchase_order_number")

    if "line_items" not in field_map:
        updated_fields.append(
            FieldDefinition(
                key="line_items",
                type="list",
                description="All invoice line items with description, quantity, unit price, and total.",
            )
        )
        added_keys.append("line_items")

    if added_keys:
        logger.warning(
            "step=schema_normalization status=augmented vendor=%s added_fields=%s",
            schema.vendor_name,
            added_keys,
        )
        return schema.model_copy(update={"fields": updated_fields})

    return schema


async def _generate_json(
    *,
    settings: Settings,
    prompt: str,
    images: Any,
    response_model: type[BaseModel],
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    provider = OpenAICompatibleDocumentProvider(settings)
    return await provider.generate_json(
        prompt=prompt,
        inputs=images,
        response_model=response_model,
        schema=get_clean_schema(response_model),
        timeout_s=timeout_s,
    )


async def identify_vendor(images: Any, *, timeout_s: float = 60.0) -> VendorIdentification:
    settings = get_settings()
    prompt = "\n".join(
        [
            "You are an expert OCR system for logistics invoices.",
            "Extract the vendor name and the header text from the document.",
            "Rules:",
            "1) Return ONLY valid JSON.",
            "2) vendor_name must be a short vendor identifier suitable for a database key.",
            "3) header_text should contain only the header area text (top of first page).",
        ]
    )
    payload = await _generate_json(
        settings=settings,
        prompt=prompt,
        images=images,
        response_model=VendorIdentification,
        timeout_s=timeout_s,
    )
    return VendorIdentification.model_validate(payload)


async def discover_schema(images: Any, *, timeout_s: float = 90.0) -> RegistrySchema:
    settings = get_settings()
    prompt = "\n".join(
        [
            "You are an AI schema discovery agent for vendor invoices.",
            "Infer a minimal field extraction schema for this vendor invoice layout.",
            "Rules:",
            "1) Return ONLY valid JSON matching RegistrySchema.",
            "2) fields must be specific, stable, and extractable from the layout.",
            "3) Use key names like invoice_number, invoice_date, total_amount, currency.",
        ]
    )
    payload = await _generate_json(
        settings=settings,
        prompt=prompt,
        images=images,
        response_model=RegistrySchema,
        timeout_s=timeout_s,
    )
    return _ensure_required_invoice_fields(RegistrySchema.model_validate(payload))


def _registry_schema_to_pydantic_model(schema: RegistrySchema) -> type[BaseModel]:
    schema = _ensure_required_invoice_fields(schema)
    fields: dict[str, tuple[Any, Any]] = {}
    for field_def in schema.fields:
        if field_def.type == "str":
            fields[field_def.key] = (str, ...)
        elif field_def.type == "float":
            fields[field_def.key] = (float, ...)
        elif field_def.type == "date":
            fields[field_def.key] = (str, ...)
        elif field_def.type == "list":
            fields[field_def.key] = (list[LineItem], ...)
        else:
            raise ValueError(f"Unsupported field type: {field_def.type}")
    return create_model(f"Extraction_{schema.vendor_name}_v{schema.version}", **fields)


async def extract_with_schema(
    images: Any,
    schema: RegistrySchema,
    *,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    settings = get_settings()
    extraction_model = _registry_schema_to_pydantic_model(schema)
    prompt = "\n".join(
        [
            "You are an elite enterprise OCR extraction engine.",
            "WARNING: The attached document may contain MULTIPLE invoices merged into one file, OR a single multi-page invoice.",
            "Rules:",
            "1) Return ONLY valid JSON matching the provided schema.",
            "2) For fields like 'line_items', you MUST extract ALL items across ALL pages of the document. Do not stop at page 1.",
            "3) Format 'line_items' as a list of JSON objects containing: description, quantity, unit_price, and total_amount.",
            "4) If there are multiple invoices, aggregate the line items, but use the Invoice Number and Dates from the FIRST invoice in the packet.",
            "5) Never invent values. Use ISO 8601 for dates (YYYY-MM-DD).",
        ]
    )
    payload = await _generate_json(
        settings=settings,
        prompt=prompt,
        images=images,
        response_model=extraction_model,
        timeout_s=timeout_s,
    )
    return extraction_model.model_validate(payload).model_dump()
