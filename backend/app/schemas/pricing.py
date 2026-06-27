from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CollectionValuationRead(BaseModel):
    collection_id: int
    collection_name: str
    total_items: int = 0
    total_quantity: int = 0
    base_value: Decimal = Decimal("0")
    sale_value: Decimal = Decimal("0")
    currency: str = "USD"
    last_price_update: datetime | None = None
    base_difference: Decimal | None = None
    base_difference_percent: Decimal | None = None


class DashboardPriceMoverRead(BaseModel):
    collection_item_id: int
    collection_id: int
    collection_name: str
    card_id: int
    card_name: str
    card_number: str
    set_name: str | None = None
    image_small: str | None = None
    image_large: str | None = None
    previous_price: Decimal
    current_price: Decimal
    difference: Decimal
    difference_percent: Decimal
    currency: str = "USD"
    from_captured_at: datetime
    to_captured_at: datetime
    trend: str


class DashboardPriceMoversRead(BaseModel):
    period_days: int = 30
    top_gainers: list[DashboardPriceMoverRead] = Field(default_factory=list)
    top_losers: list[DashboardPriceMoverRead] = Field(default_factory=list)


class CollectionRefreshPricesResponse(BaseModel):
    collection_id: int
    collection_name: str
    processed_items: int
    updated_items: int
    items_without_price: int
    items_failed: int = 0
    base_value: Decimal = Decimal("0")
    sale_value: Decimal = Decimal("0")
    currency: str = "USD"
    captured_at: datetime


class PriceHistoryEntryRead(BaseModel):
    captured_at: datetime
    base_price: Decimal | None = None
    sale_price: Decimal | None = None
    currency: str = "USD"


class CollectionItemVariationRead(BaseModel):
    collection_item_id: int
    card_name: str
    previous_price: Decimal | None = None
    current_price: Decimal | None = None
    difference: Decimal | None = None
    difference_percent: Decimal | None = None
    previous_total: Decimal | None = None
    current_total: Decimal | None = None
    currency: str = "USD"
    trend: str


class CollectionPriceVariationRead(BaseModel):
    collection_id: int
    collection_name: str
    total_items: int
    items_up: int
    items_down: int
    items_equal: int
    items_without_history: int
    total_previous_base_value: Decimal = Decimal("0")
    total_current_base_value: Decimal = Decimal("0")
    total_difference: Decimal = Decimal("0")
    total_difference_percent: Decimal | None = None
    top_increases: list[CollectionItemVariationRead] = Field(default_factory=list)
    top_decreases: list[CollectionItemVariationRead] = Field(default_factory=list)
    item_variations: list[CollectionItemVariationRead] = Field(default_factory=list)
