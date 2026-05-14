from pydantic import BaseModel

from src.core.nodes import (
    _ensure_required_invoice_fields,
    _registry_schema_to_pydantic_model,
    get_clean_schema,
)
from src.schemas import FieldDefinition, RegistrySchema


def test_registry_schema_to_model_and_clean_schema() -> None:
    schema = RegistrySchema(
        vendor_name="DHL_Express",
        version=1,
        fields=[
            FieldDefinition(key="invoice_number", type="str", description="Header"),
            FieldDefinition(key="total_amount", type="float", description="Bottom right"),
            FieldDefinition(key="items", type="list", description="Line items"),
        ],
    )
    model: type[BaseModel] = _registry_schema_to_pydantic_model(schema)
    json_schema = get_clean_schema(model)
    schema_str = str(json_schema).lower()
    assert "default" not in schema_str
    assert "minlength" not in schema_str
    assert "$defs" not in schema_str
    assert "$ref" not in schema_str
    assert "invoice_number" in json_schema.get("properties", {})


def test_invoice_schema_is_augmented_with_required_fields() -> None:
    schema = RegistrySchema(
        vendor_name="LABEL_TECH",
        version=1,
        fields=[
            FieldDefinition(key="invoice_number", type="str", description="Header"),
            FieldDefinition(key="total_amount", type="float", description="Total"),
        ],
    )

    normalized = _ensure_required_invoice_fields(schema)
    field_keys = [field.key for field in normalized.fields]

    assert "purchase_order_number" in field_keys
    assert "line_items" in field_keys
