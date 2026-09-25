from __future__ import annotations

import pytest

from src.config import Settings
from src.infrastructure.paddle_document_provider import PaddleDocumentIntelligenceProvider
from src.providers.factory import build_document_provider


def test_factory_builds_paddle_provider_by_default() -> None:
    provider = build_document_provider(Settings())

    assert isinstance(provider, PaddleDocumentIntelligenceProvider)
    assert provider.provider_id == "paddle_local_rules"


def test_settings_reject_unknown_document_provider() -> None:
    with pytest.raises(ValueError):
        Settings(document_provider="unknown")  # type: ignore[arg-type]
