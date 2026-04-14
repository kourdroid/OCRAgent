from pydantic import BaseModel

from src.core.nodes import get_clean_schema, _registry_schema_to_pydantic_model
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
