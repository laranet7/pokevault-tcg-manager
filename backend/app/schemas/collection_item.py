from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.card import CardRead, CardUpsertPayload


class CollectionItemBase(BaseModel):
    quantity: int = Field(default=1, ge=1)
    language: str | None = None
    condition: str | None = None
    finish: str | None = None
    is_pokeball: bool = False
    is_for_sale: bool = False
    base_price: Decimal | None = Field(default=None, ge=0)
    base_price_currency: str = "USD"
    sale_margin_percent: Decimal | None = Field(default=None, ge=0)
    sale_price: Decimal | None = Field(default=None, ge=0)
    sale_status: str | None = "not_available"
    notes: str | None = None

    @field_validator("base_price", "sale_margin_percent", "sale_price", mode="before")
    @classmethod
    def normalize_decimal(cls, value: Decimal | float | str | None) -> Decimal | None:
        if value is None or value == "":
            return None
        return Decimal(str(value))

    @model_validator(mode="after")
    def compute_sale_price(self) -> "CollectionItemBase":
        if self.sale_price is None and self.base_price is not None and self.sale_margin_percent is not None:
            multiplier = Decimal("1") + (self.sale_margin_percent / Decimal("100"))
            self.sale_price = (self.base_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return self


class CollectionItemCreate(CollectionItemBase):
    card: CardUpsertPayload


class CollectionItemUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=1)
    language: str | None = None
    condition: str | None = None
    finish: str | None = None
    is_pokeball: bool | None = None
    is_for_sale: bool | None = None
    base_price: Decimal | None = Field(default=None, ge=0)
    base_price_currency: str | None = None
    sale_margin_percent: Decimal | None = Field(default=None, ge=0)
    sale_price: Decimal | None = Field(default=None, ge=0)
    sale_status: str | None = None
    notes: str | None = None

    @field_validator("base_price", "sale_margin_percent", "sale_price", mode="before")
    @classmethod
    def normalize_decimal(cls, value: Decimal | float | str | None) -> Decimal | None:
        if value is None or value == "":
            return None
        return Decimal(str(value))


class CollectionItemsMoveRequest(BaseModel):
    item_ids: list[int] = Field(min_length=1)
    target_collection_id: int = Field(ge=1)


class CollectionItemsMoveResponse(BaseModel):
    moved_items: int
    merged_items: int
    target_collection_id: int


class CollectionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    collection_id: int
    card_id: int
    quantity: int
    language: str | None = None
    condition: str | None = None
    finish: str | None = None
    is_pokeball: bool
    is_for_sale: bool
    base_price: Decimal | None = None
    base_price_currency: str
    tcgplayer_price: Decimal | None = None
    tcgplayer_currency: str | None = None
    tcgplayer_price_label: str | None = None
    cardmarket_price: Decimal | None = None
    cardmarket_currency: str | None = None
    cardmarket_price_label: str | None = None
    sale_margin_percent: Decimal | None = None
    sale_price: Decimal | None = None
    sale_status: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    card: CardRead


class InventorySearchResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    collection_id: int
    collection_name: str
    quantity: int
    language: str | None = None
    condition: str | None = None
    finish: str | None = None
    is_pokeball: bool
    is_for_sale: bool
    base_price: Decimal | None = None
    base_price_currency: str
    sale_price: Decimal | None = None
    sale_status: str | None = None
    notes: str | None = None
    card: CardRead
