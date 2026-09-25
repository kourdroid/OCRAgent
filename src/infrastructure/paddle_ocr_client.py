from __future__ import annotations

import httpx
from pydantic import ValidationError

from src.providers.base import RetryableProviderError, TerminalProviderError
from src.providers.ocr import OCRDocument


class PaddleOCRClient:
    provider_id = "paddle_ocr"

    def __init__(
        self,
        *,
        base_url: str,
        model_id: str,
        timeout_s: float,
    ) -> None:
        self.model_id = model_id
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_s)

    async def healthcheck(self) -> dict[str, str | bool]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/health")
                response.raise_for_status()
                payload = response.json()
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise RetryableProviderError(f"PaddleOCR is unavailable: {exc}") from exc
        except (httpx.HTTPStatusError, ValueError) as exc:
            raise TerminalProviderError(f"PaddleOCR health response is invalid: {exc}") from exc

        return {
            "ok": bool(payload.get("ready")),
            "provider": self.provider_id,
            "model": str(payload.get("model_id") or self.model_id),
        }

    async def recognize_pdf(self, pdf_bytes: bytes) -> OCRDocument:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/v1/ocr",
                    files={"file": ("document.pdf", pdf_bytes, "application/pdf")},
                )
                response.raise_for_status()
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise RetryableProviderError(f"PaddleOCR request failed: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            message = exc.response.text[:500]
            if exc.response.status_code >= 500:
                raise RetryableProviderError(
                    f"PaddleOCR returned {exc.response.status_code}: {message}"
                ) from exc
            raise TerminalProviderError(
                f"PaddleOCR rejected the document ({exc.response.status_code}): {message}"
            ) from exc

        try:
            return OCRDocument.model_validate(response.json())
        except (ValidationError, ValueError) as exc:
            raise TerminalProviderError("PaddleOCR returned an invalid result") from exc
