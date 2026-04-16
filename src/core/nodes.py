from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import random
import re
import time
import base64
import io
from typing import Any

from pydantic import BaseModel, Field, create_model

from src.config import Settings, get_settings
from src.schemas import RegistrySchema

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
    Prioritizes the primary model, then falls back to stable production models.
    """
    candidates = [primary]
    
    # Fallback hierarchy:
    # 1. gemini-3-flash-preview: Latest preview (User Requested).
    # 2. gemini-2.0-flash: Next-gen, fast, stable.
    # 3. gemini-2.0-flash-lite: Low cost backup.
    # NOTE: gemini-1.5-flash removed due to v1beta 404 errors.
    
    defaults = [
        "gemini-3-flash-preview",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite"
    ]
    
    candidates.extend(defaults)

    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


async def _generate_json_openrouter(
    *,
    settings: Settings,
    prompt: str,
    images: list[Any] | Any,
    response_model: type[BaseModel],
    timeout_s: float,
) -> dict[str, Any]:
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )
    
    content_list: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    
    img_list = images if isinstance(images, list) else [images]
    for img in img_list:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        content_list.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})
    
    schema_dict = get_clean_schema(response_model)
    messages = [
        {
            "role": "user",
            "content": content_list
        }
    ]
    model_name = settings.model_name
    
    # If using OpenRouter with a generic Gemini model string from .env, 
    # OpenRouter requires the 'google/' provider prefix
    if "gemini" in model_name and "google/" not in model_name: 
        model_name = f"google/{model_name}"

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model_name,
                messages=messages, # type: ignore
                temperature=settings.temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "extraction_schema",
                        "strict": False,
                        "schema": schema_dict
                    }
                }
            ),
            timeout=timeout_s,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Empty response from OpenRouter")
        return json.loads(content)
    except Exception as exc:
        logger.error(f"step=openrouter_call model={model_name} error={str(exc)}")
        raise

async def _generate_json(
    *,
    settings: Settings,
    prompt: str,
    images: list[Any] | Any,
    response_model: type[BaseModel],
    timeout_s: float,
) -> dict[str, Any]:
    from google.genai import types
    has_part = isinstance(images, types.Part) or (isinstance(images, list) and any(isinstance(img, types.Part) for img in images))

    if settings.openrouter_api_key and not has_part:
        return await _generate_json_openrouter(
            settings=settings,
            prompt=prompt,
            images=images,
            response_model=response_model,
            timeout_s=timeout_s
        )

    if not settings.google_api_key:
        raise RuntimeError("No Google API key and no OpenRouter API key provided.")

    from google import genai
    from google.genai import errors, types

    client = genai.Client(api_key=settings.google_api_key)
    
    # We track the last error to raise it if all strategies fail
    last_error: Exception | None = None
    
    # Global timeout tracker to ensure we don't loop forever
    overall_start = time.monotonic()

    candidates = _model_name_candidates(settings.model_name)
    
    for model_name in candidates:
        # Check if we have burned through the total function timeout
        if (time.monotonic() - overall_start) > timeout_s:
            logger.error("step=gemini_call status=global_timeout_exceeded")
            break

        # Max retries PER MODEL to handle transient 429s
        max_retries = 3
        base_delay = 2.0  # Start with 2 seconds

        for attempt in range(max_retries + 1):
            start = time.monotonic()
            try:
                logger.info(
                    "step=gemini_call model=%s attempt=%d/%d status=start",
                    model_name, attempt + 1, max_retries + 1
                )
                
                # Calculate remaining timeout for this specific call
                time_spent = time.monotonic() - overall_start
                remaining_timeout = max(5.0, timeout_s - time_spent)

                img_list = images if isinstance(images, list) else [images]
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=model_name,
                        contents=[prompt, *img_list],
                        config=types.GenerateContentConfig(
                            temperature=settings.temperature,
                            response_mime_type="application/json",
                            response_schema=response_model,
                        ),
                    ),
                    timeout=remaining_timeout,
                )
                
                elapsed_ms = int((time.monotonic() - start) * 1000)
                logger.info(
                    "step=gemini_call model=%s status=success duration_ms=%s",
                    model_name, elapsed_ms
                )

                if response.parsed:
                    return response.parsed.model_dump()
                return json.loads(response.text)

            except asyncio.TimeoutError as exc:
                logger.warning("step=gemini_call model=%s status=timeout", model_name)
                last_error = exc
                # Timeouts usually imply the model is hanging, switching might be better than retrying the same one
                break

            except errors.APIError as exc:
                last_error = exc
                code = getattr(exc, "code", 0)
                message = getattr(exc, "message", str(exc))
                
                # Handle Rate Limits (429) specifically
                if code == 429:
                    if attempt < max_retries:
                        # Extract retry delay from error message or default to backoff
                        # Pattern matches "Please retry in 41.09s" or similar
                        delay_match = re.search(r"retry in (\d+(\.\d+)?)s", message)
                        
                        if delay_match:
                            wait_s = float(delay_match.group(1)) + 1.0  # Add 1s buffer
                        else:
                            # Exponential backoff with jitter: 2s, 4s, 8s... + jitter
                            wait_s = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                        
                        logger.warning(
                            "step=gemini_call model=%s status=rate_limited wait_s=%.2f message='%s'",
                            model_name, wait_s, message
                        )
                        await asyncio.sleep(wait_s)
                        continue
                    else:
                        logger.error("step=gemini_call model=%s status=rate_limit_exhausted", model_name)
                        # Fallthrough to try the next model in the candidate list
                
                # Handle 5xx errors (Server Errors) - sometimes worth a retry
                elif code >= 500:
                    logger.warning("step=gemini_call model=%s status=server_error code=%s", model_name, code)
                    await asyncio.sleep(1) # Short sleep for server hiccups
                    continue # Retry same model
                
                # Handle 4xx errors (Bad Request) - Do not retry, do not switch models (usually logic error)
                elif 400 <= code < 500:
                    logger.error("step=gemini_call model=%s status=bad_request code=%s message=%s", model_name, code, message)
                    raise exc # Fatal error, stop everything

                # For other errors, log and try next model
                logger.warning("step=gemini_call model=%s status=api_error_next_model code=%s", model_name, code)
                break
            
            except Exception as exc:
                last_error = exc
                logger.warning("step=gemini_call model=%s status=unexpected_error error=%s", model_name, str(exc))
                break # Try next model

    if last_error:
        raise last_error

    raise RuntimeError("Gemini call failed: No models available or global timeout exceeded")


async def identify_vendor(image: Any, *, timeout_s: float = 60.0) -> VendorIdentification:
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
        images=image,
        response_model=VendorIdentification,
        timeout_s=timeout_s,
    )
    return VendorIdentification.model_validate(payload)


async def discover_schema(image: Any, *, timeout_s: float = 90.0) -> RegistrySchema:
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
        images=image,
        response_model=RegistrySchema,
        timeout_s=timeout_s,
    )
    return RegistrySchema.model_validate(payload)


async def detect_drift(
    image: Any,
    *,
    existing_fingerprint_hash: str,
    timeout_s: float = 60.0,
) -> tuple[bool, float, str]:
    vendor = await identify_vendor(image, timeout_s=timeout_s)
    new_fingerprint = compute_fingerprint(vendor.header_text)
    drifted = new_fingerprint != existing_fingerprint_hash
    confidence = 1.0 if not drifted else 0.0
    return drifted, confidence, new_fingerprint


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
            fields[field_def.key] = (list[str], ...)
        else:
            raise ValueError(f"Unsupported field type: {field_def.type}")
    return create_model(f"Extraction_{schema.vendor_name}_v{schema.version}", **fields)  # type: ignore[arg-type]


async def extract_with_schema(
    images: list[Any] | Any,
    schema: RegistrySchema,
    *,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    settings = get_settings()
    extraction_model = _registry_schema_to_pydantic_model(schema)
    prompt = "\n".join(
        [
            "You are an OCR extraction engine specialized in logistics invoices.",
            "Extract the requested fields from the document.",
            "Rules:",
            "1) Return ONLY valid JSON matching the provided schema.",
            "2) Use ISO 8601 for dates (YYYY-MM-DD) when relevant.",
            "3) Never invent values; if a field is missing, make your best effort from visible text.",
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
