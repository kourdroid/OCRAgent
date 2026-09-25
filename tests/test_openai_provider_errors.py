from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from src.config import Settings
from src.infrastructure.openai_provider import OpenAICompatibleDocumentProvider
from src.providers.base import RetryableProviderError, TerminalProviderError


class _ResponseModel(BaseModel):
    value: str


class _ProviderError(Exception):
    def __init__(self, *, status_code: int, code: str) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.body = {
            "error": {
                "message": code,
                "type": code,
                "code": code,
            }
        }


class _Completions:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    async def create(self, **_kwargs: Any) -> None:
        self.calls += 1
        raise self.error


class _Chat:
    def __init__(self, completions: _Completions) -> None:
        self.completions = completions


class _Client:
    def __init__(self, completions: _Completions) -> None:
        self.chat = _Chat(completions)


def _provider(error: Exception) -> tuple[OpenAICompatibleDocumentProvider, _Completions]:
    provider = OpenAICompatibleDocumentProvider(Settings(llm_api_key="test"))
    completions = _Completions(error)
    provider._client = _Client(completions)  # type: ignore[assignment]
    return provider, completions


@pytest.mark.asyncio
async def test_insufficient_quota_is_terminal_without_retry() -> None:
    provider, completions = _provider(
        _ProviderError(status_code=429, code="insufficient_quota")
    )

    with pytest.raises(TerminalProviderError, match="quota is unavailable"):
        await provider.generate_json(
            prompt="test",
            inputs=[],
            response_model=_ResponseModel,
            schema=_ResponseModel.model_json_schema(),
            timeout_s=1,
        )

    assert completions.calls == 1


@pytest.mark.asyncio
async def test_rate_limit_remains_retryable(monkeypatch) -> None:
    provider, completions = _provider(
        _ProviderError(status_code=429, code="rate_limit_exceeded")
    )

    async def no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr("src.infrastructure.openai_provider.asyncio.sleep", no_sleep)

    with pytest.raises(RetryableProviderError, match="rate_limit_exceeded"):
        await provider.generate_json(
            prompt="test",
            inputs=[],
            response_model=_ResponseModel,
            schema=_ResponseModel.model_json_schema(),
            timeout_s=1,
        )

    assert completions.calls == 3
