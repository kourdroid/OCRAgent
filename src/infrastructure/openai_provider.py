from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
from typing import Any

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel

from src.config import Settings
from src.dossiers.models import DocumentClassification, DocumentExtraction, DocumentType
from src.providers.base import (
    ProviderCapabilities,
    RetryableProviderError,
    TerminalProviderError,
)

logger = logging.getLogger(__name__)

_TERMINAL_QUOTA_CODES = {
    "billing_hard_limit_reached",
    "insufficient_quota",
}


def _provider_error_code(exc: Exception) -> str | None:
    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return None
    error = body.get("error", body)
    if not isinstance(error, dict):
        return None
    code = error.get("code") or error.get("type")
    return str(code) if code else None


def _normalize_inputs(inputs: Any) -> list[dict[str, Any]]:
    input_list = inputs if isinstance(inputs, list) else [inputs]
    result: list[dict[str, Any]] = []

    for item in input_list:
        if hasattr(item, "mime_type") and hasattr(item, "data"):
            mime_type = getattr(item, "mime_type", "") or ""
            data = getattr(item, "data", b"") or b""
            if mime_type == "application/pdf" and data:
                encoded = base64.b64encode(data).decode("ascii")
                result.append(
                    {
                        "type": "file",
                        "file": {
                            "filename": "document.pdf",
                            "file_data": f"data:application/pdf;base64,{encoded}",
                        },
                    }
                )
            elif mime_type.startswith("image/") and data:
                encoded = base64.b64encode(data).decode("ascii")
                result.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                    }
                )
        elif hasattr(item, "save"):
            buffer = io.BytesIO()
            item.save(buffer, format="JPEG")
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            result.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                }
            )
        elif isinstance(item, dict):
            result.append(item)
        elif isinstance(item, str):
            result.append({"type": "text", "text": item})

    return result


class _PdfPart:
    mime_type = "application/pdf"

    def __init__(self, data: bytes) -> None:
        self.data = data


class OpenAICompatibleDocumentProvider:
    provider_id = "openai_compatible"
    capabilities = ProviderCapabilities(
        pdf_input=True,
        image_input=True,
        structured_output=True,
        bounding_boxes=True,
    )

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model_id = settings.model_name
        api_key = settings.llm_api_key
        if not api_key and settings.llm_api_key_required:
            raise TerminalProviderError(
                "No LLM API key provided. Set LLM_API_KEY or disable "
                "LLM_API_KEY_REQUIRED for an unauthenticated local endpoint."
            )

        client_kwargs: dict[str, Any] = {"api_key": api_key or "local"}
        if settings.llm_base_url:
            client_kwargs["base_url"] = settings.llm_base_url
        self._client = AsyncOpenAI(**client_kwargs, max_retries=0)

    async def healthcheck(self) -> dict[str, str | bool]:
        return {
            "ok": True,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
        }

    async def generate_json(
        self,
        *,
        prompt: str,
        inputs: Any,
        response_model: type[BaseModel],
        schema: dict[str, Any],
        timeout_s: float,
    ) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        content.extend(_normalize_inputs(inputs))

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await asyncio.wait_for(
                    self._client.chat.completions.create(
                        model=self.model_id,
                        messages=[{"role": "user", "content": content}],
                        temperature=self._settings.temperature,
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": response_model.__name__.lower(),
                                "strict": False,
                                "schema": schema,
                            },
                        },
                    ),
                    timeout=timeout_s,
                )
                payload = response.choices[0].message.content
                if not payload:
                    raise TerminalProviderError("Document provider returned an empty response")
                return json.loads(payload)
            except asyncio.TimeoutError as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
                    continue
                raise RetryableProviderError("Document provider timed out") from exc
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
                    continue
                raise RetryableProviderError("Document provider network failure") from exc
            except json.JSONDecodeError as exc:
                raise TerminalProviderError("Document provider returned invalid JSON") from exc
            except (RetryableProviderError, TerminalProviderError):
                raise
            except Exception as exc:
                last_error = exc
                status_code = getattr(exc, "status_code", None)
                error_code = _provider_error_code(exc)
                if status_code == 429 and error_code in _TERMINAL_QUOTA_CODES:
                    raise TerminalProviderError(
                        f"Document provider quota is unavailable ({error_code})"
                    ) from exc
                retryable = status_code == 429 or (
                    isinstance(status_code, int) and status_code >= 500
                )
                if retryable and attempt < 2:
                    await asyncio.sleep(2**attempt)
                    continue
                if retryable:
                    raise RetryableProviderError(str(exc)) from exc
                raise TerminalProviderError(str(exc)) from exc

        raise RetryableProviderError("Document provider retries exhausted") from last_error

    async def classify_pdf(
        self,
        pdf_bytes: bytes,
        *,
        page_count: int,
        supported_types: frozenset[DocumentType],
    ) -> DocumentClassification:
        supported = ", ".join(sorted(item.value for item in supported_types))
        prompt = "\n".join(
            [
                "Classify every page in this Moroccan import dossier.",
                f"The PDF has exactly {page_count} page(s).",
                f"Allowed document types: {supported}.",
                "Return contiguous page segments. Every page must appear exactly once.",
                "Use UNKNOWN when the type or a page boundary is uncertain.",
                "Confidence must be between 0 and 1.",
            ]
        )
        schema = DocumentClassification.model_json_schema()
        payload = await self.generate_json(
            prompt=prompt,
            inputs=_PdfPart(pdf_bytes),
            response_model=DocumentClassification,
            schema=schema,
            timeout_s=120.0,
        )
        return DocumentClassification.model_validate(payload)

    async def extract_pdf(
        self,
        pdf_bytes: bytes,
        *,
        document_type: DocumentType,
        allowed_fields: tuple[str, ...],
    ) -> DocumentExtraction:
        fields = ", ".join(allowed_fields) or "none"
        prompt = "\n".join(
            [
                f"Extract normalized facts from a {document_type.value} document.",
                f"Allowed field_path values for this type: {fields}.",
                "Return only facts visibly supported by the document.",
                "For every fact include the local PDF page, exact source text, confidence,",
                "and a normalized [x1, y1, x2, y2] bounding box when available.",
                "Never invent missing values.",
            ]
        )
        schema = DocumentExtraction.model_json_schema()
        payload = await self.generate_json(
            prompt=prompt,
            inputs=_PdfPart(pdf_bytes),
            response_model=DocumentExtraction,
            schema=schema,
            timeout_s=120.0,
        )
        extraction = DocumentExtraction.model_validate(payload)
        if extraction.document_type is not document_type:
            raise TerminalProviderError(
                f"Extraction type mismatch: expected {document_type}, "
                f"received {extraction.document_type}"
            )
        unexpected_fields = {
            fact.field_path for fact in extraction.facts if fact.field_path not in allowed_fields
        }
        if unexpected_fields:
            raise TerminalProviderError(
                f"Provider returned unsupported fields for {document_type}: "
                f"{sorted(unexpected_fields)}"
            )
        return extraction
