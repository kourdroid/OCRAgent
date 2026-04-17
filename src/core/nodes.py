from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import io
import json
import logging
import re
import time
from typing import Any

from pydantic import BaseModel, Field, create_model

from src.config import Settings, get_settings
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


def _model_name_candidates(primary: str) -> list[str]:
    """
    Returns a list of model names to try in order.
    Primary comes from MODEL_NAME in .env. No hardcoded fallbacks.
    """
    return [primary]


def _part_to_content_dict(part: Any) -> dict[str, Any]:
    """
    Convert a google.genai.types.Part (or any object with .mime_type and .data)
    into an OpenRouter-compatible message content dict.
    """
    mime_type = getattr(part, "mime_type", "") or ""
    data_bytes = getattr(part, "data", b"") or b""

    if not data_bytes:
        return {"type": "text", "text": ""}

    b64 = base64.b64encode(data_bytes).decode("utf-8")

    if mime_type == "application/pdf":
        return {
            "type": "file",
            "file": {
                "filename": "document.pdf",
                "file_data": f"data:application/pdf;base64,{b64}",
            },
        }

    if mime_type.startswith("image/"):
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
        }

    return {"type": "text", "text": f"[Unsupported mime type: {mime_type}]"}


def _normalize_images_for_openrouter(images: Any) -> list[dict[str, Any]]:
    """
    Convert a list of Parts / PIL Images / base64 strings into
    OpenRouter-compatible content dicts.
    """
    img_list = images if isinstance(images, list) else [images]
    result: list[dict[str, Any]] = []

    for img in img_list:
        if hasattr(img, "mime_type") and hasattr(img, "data"):
            result.append(_part_to_content_dict(img))
        elif hasattr(img, "save"):
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            result.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        elif isinstance(img, str):
            result.append({"type": "text", "text": img})
        elif isinstance(img, dict):
            result.append(img)

    return result


async def _generate_json(
    *,
    settings: Settings,
    prompt: str,
    images: Any,
    response_model: type[BaseModel],
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    from openai import AsyncOpenAI

    if not settings.openrouter_api_key:
        raise RuntimeError("No OpenRouter API key provided. Set OPENROUTER_API_KEY in your environment.")

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )

    schema_dict = get_clean_schema(response_model)

    content_parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    content_parts.extend(_normalize_images_for_openrouter(images))

    candidates = _model_name_candidates(settings.model_name)

    last_error: Exception | None = None
    overall_start = time.monotonic()

    for model_name in candidates:
        if (time.monotonic() - overall_start) > timeout_s:
            logger.error("step=openrouter_call status=global_timeout_exceeded")
            break

        max_retries = 3
        base_delay = 2.0

        for attempt in range(max_retries + 1):
            start = time.monotonic()

            try:
                remaining_timeout = max(5.0, timeout_s - (time.monotonic() - overall_start))

                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": content_parts}],
                        temperature=settings.temperature,
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": "extraction_schema",
                                "strict": False,
                                "schema": schema_dict,
                            },
                        },
                    ),
                    timeout=remaining_timeout,
                )

                elapsed_ms = int((time.monotonic() - start) * 1000)
                logger.info(
                    "step=openrouter_call model=%s status=success duration_ms=%s",
                    model_name, elapsed_ms,
                )

                content = response.choices[0].message.content
                if not content:
                    raise RuntimeError("Empty response from OpenRouter")

                return json.loads(content)

            except asyncio.TimeoutError:
                logger.warning("step=openrouter_call model=%s status=timeout", model_name)
                last_error = Exception("TimeoutError")
                break

            except Exception as exc:
                last_error = exc
                error_str = str(exc).lower()

                if "429" in error_str or "rate" in error_str or "quota" in error_str:
                    if attempt < max_retries:
                        delay_match = re.search(r"retry in (\d+(\.\d+)?)s", error_str)
                        if delay_match:
                            wait_s = float(delay_match.group(1)) + 1.0
                        else:
                            wait_s = (base_delay * (2 ** attempt)) + 0.5
                        logger.warning(
                            "step=openrouter_call model=%s status=rate_limited wait_s=%.2f",
                            model_name, wait_s,
                        )
                        await asyncio.sleep(wait_s)
                        continue
                    else:
                        logger.error("step=openrouter_call model=%s status=rate_limit_exhausted", model_name)

                elif "5" in error_str or "server error" in error_str:
                    logger.warning("step=openrouter_call model=%s status=server_error", model_name)
                    await asyncio.sleep(1)
                    continue

                else:
                    logger.warning(
                        "step=openrouter_call model=%s status=api_error error=%s",
                        model_name, str(exc),
                    )

                break

    if last_error:
        raise last_error

    raise RuntimeError("OpenRouter call failed: all models exhausted or global timeout exceeded")


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
    return RegistrySchema.model_validate(payload)


def _registry_schema_to_pydantic_model(schema: RegistrySchema) -> type[BaseModel]:
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
            "3) Format 'line_items' as a list of JSON objects containing: description, quantity, unit_price, and total.",
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
    return payload
