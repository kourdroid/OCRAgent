from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from src.config import Settings
from src.core.nodes import extract_with_schema
from src.schemas import FieldDefinition, RegistrySchema


def _schema() -> RegistrySchema:
    return RegistrySchema(
        vendor_name="DHL_Express",
        fields=[
            FieldDefinition(
                key="invoice_number",
                type="str",
                description="Invoice identifier",
            ),
            FieldDefinition(
                key="total_amount",
                type="float",
                description="Invoice total",
            ),
        ],
        version=1,
    )


@pytest.mark.asyncio
async def test_extract_with_schema_returns_validated_model_dump(monkeypatch) -> None:
    async def fake_generate_json(**_kwargs: Any) -> dict[str, Any]:
        return {
            "invoice_number": "INV-1",
            "total_amount": "123.45",
            "purchase_order_number": "PO-1",
            "line_items": [],
        }

    monkeypatch.setattr("src.core.nodes.get_settings", lambda: Settings(llm_api_key="x"))
    monkeypatch.setattr("src.core.nodes._generate_json", fake_generate_json)

    result = await extract_with_schema(object(), _schema())

    assert result == {
        "invoice_number": "INV-1",
        "total_amount": 123.45,
        "purchase_order_number": "PO-1",
        "line_items": [],
    }


@pytest.mark.asyncio
async def test_extract_with_schema_rejects_invalid_llm_payload(monkeypatch) -> None:
    async def fake_generate_json(**_kwargs: Any) -> dict[str, Any]:
        return {
            "invoice_number": "INV-1",
            "total_amount": "not-a-number",
            "purchase_order_number": "PO-1",
            "line_items": [],
        }

    monkeypatch.setattr("src.core.nodes.get_settings", lambda: Settings(llm_api_key="x"))
    monkeypatch.setattr("src.core.nodes._generate_json", fake_generate_json)

    with pytest.raises(ValidationError):
        await extract_with_schema(object(), _schema())

