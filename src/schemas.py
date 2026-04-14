"""
Pydantic schemas for Ironclad-OCR.
Defines the DNA of valid invoice data with self-healing validators.
"""
from __future__ import annotations

import logging
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class FieldDefinition(BaseModel):
    key: str
    type: Literal["str", "float", "date", "list"]
    description: str


class RegistrySchema(BaseModel):
    vendor_name: str
    fields: List[FieldDefinition]
    version: int = 1


class LineItem(BaseModel):
    """
    Represents a single line item on an invoice.
    Includes self-healing math validation.
    """
    description: str = Field(..., description="Item name or description")
    quantity: float = Field(..., description="Count of items")
    unit_price: float = Field(..., description="Price per single unit")
    total_amount: float = Field(..., description="Calculated total for this line")

    @model_validator(mode='after')
    def check_math(self) -> 'LineItem':
        """
        The Ruthless Logic Check: Does Qty * Price == Total?
        Self-heals if within tolerance, otherwise corrects the value.
        """
        calculated = self.quantity * self.unit_price
        diff = abs(calculated - self.total_amount)
        
        if diff > 0.05:
            logging.getLogger(__name__).warning(
                "Auto-fixing math for %s: %s -> %s",
                self.description,
                self.total_amount,
                round(calculated, 2),
            )
            object.__setattr__(self, 'total_amount', round(calculated, 2))
        return self


class Invoice(BaseModel):
    """
    The complete invoice schema.
    Enforces strict typing for all extracted data.
    """
    invoice_number: str = Field(..., description="Unique invoice identifier")
    date: str = Field(..., description="Invoice date in ISO 8601 format YYYY-MM-DD")
    vendor_name: str = Field(..., description="Name of the vendor/supplier")
    currency: str = Field(default="USD", description="ISO 4217 Currency Code")
    line_items: List[LineItem] = Field(default_factory=list, description="List of invoice line items")
    subtotal: float = Field(..., description="Sum of all line items before tax")
    tax_amount: float = Field(default=0.0, description="Total tax amount")
    grand_total: float = Field(..., description="Final total including tax")

    @model_validator(mode='after')
    def validate_totals(self) -> 'Invoice':
        """
        Validates that line items sum to subtotal and subtotal + tax = grand_total.
        """
        if self.line_items:
            calculated_subtotal = sum(item.total_amount for item in self.line_items)
            diff = abs(calculated_subtotal - self.subtotal)
            if diff > 0.10:
                logging.getLogger(__name__).warning(
                    "Subtotal mismatch: items=%s invoice=%s",
                    calculated_subtotal,
                    self.subtotal,
                )
        
        calculated_grand = self.subtotal + self.tax_amount
        diff = abs(calculated_grand - self.grand_total)
        if diff > 0.10:
            logging.getLogger(__name__).warning(
                "Grand total mismatch: subtotal=%s tax=%s calc=%s invoice=%s",
                self.subtotal,
                self.tax_amount,
                calculated_grand,
                self.grand_total,
            )
        
        return self
