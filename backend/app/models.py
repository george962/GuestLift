"""Canonical (GRDC draft) models used by both source adapters."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class Item(BaseModel):
    item_id: str
    name: str
    quantity: float = Field(gt=0)
    gross_minor: int = Field(ge=0)
    discount_minor: int = Field(ge=0)


class Payment(BaseModel):
    payment_id: str
    amount_minor: int = Field(ge=0)
    status: str


class CanonicalOrder(BaseModel):
    provider: Literal["toast", "square"]
    source_order_id: str
    location_id: str
    created_at: str
    currency: str = "USD"
    status: str
    gross_minor: int = Field(ge=0)
    discount_minor: int = Field(ge=0)
    refund_minor: int = Field(ge=0)
    net_sales_minor: int = Field(ge=0)
    tax_minor: int | None = None
    tip_minor: int | None = None
    items: list[Item]
    payments: list[Payment]
    lineage: dict[str, str]
    warnings: list[str] = Field(default_factory=list)


class ImportResult(BaseModel):
    provider: Literal["toast", "square"]
    status: Literal["completed", "replayed"]
    inserted: int
    duplicates: int
    rejected: int
    issues: list[str]
    orders: list[CanonicalOrder]
    import_id: str
