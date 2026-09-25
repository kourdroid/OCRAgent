from __future__ import annotations

from decimal import Decimal

from src.infrastructure.dossier_repos import _serialize_row


def test_serialize_row_converts_postgres_decimal_to_json_number() -> None:
    result = _serialize_row(
        {
            "classification_confidence": Decimal("0.95"),
            "gross_weight": Decimal("20822.0"),
        }
    )

    assert result == {
        "classification_confidence": 0.95,
        "gross_weight": 20822.0,
    }
