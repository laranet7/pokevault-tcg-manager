from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.card import CardRead, CardUpsertPayload


CollectionPatternVariant = Literal["poke_ball", "master_ball"]


class CollectionItemBase(BaseModel):
    quantity: int = Field(default=1, ge=1)
    language: str | None = None
    condition: str | None = None
    finish: str | None = None
    pattern_variant: CollectionPatternVariant | None = None
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

    @field_validator("pattern_variant", mode="before")
    @classmethod
    def normalize_pattern_variant(cls, value: str | bool | None) -> CollectionPatternVariant | None:
        if value in (None, "", False):
            return None
        if value is True:
            return "poke_ball"

        normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        alias_map = {
            "none": None,
            "null": None,
            "pokeball": "poke_ball",
            "poke_ball": "poke_ball",
            "poke_ball_pattern": "poke_ball",
            "masterball": "master_ball",
            "master_ball": "master_ball",
            "master_ball_pattern": "master_ball",
        }
        return alias_map.get(normalized, normalized)  # type: ignore[return-value]

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
    pattern_variant: CollectionPatternVariant | None = None
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

    @field_validator("pattern_variant", mode="before")
    @classmethod
    def normalize_pattern_variant(cls, value: str | bool | None) -> CollectionPatternVariant | None:
        if value in (None, "", False):
            return None
        if value is True:
            return "poke_ball"

        normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        alias_map = {
            "none": None,
            "null": None,
            "pokeball": "poke_ball",
            "poke_ball": "poke_ball",
            "poke_ball_pattern": "poke_ball",
            "masterball": "master_ball",
            "master_ball": "master_ball",
            "master_ball_pattern": "master_ball",
        }
        return alias_map.get(normalized, normalized)  # type: ignore[return-value]


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
    pattern_variant: CollectionPatternVariant | None = None
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
    pattern_variant: CollectionPatternVariant | None = None
    is_for_sale: bool
    base_price: Decimal | None = None
    base_price_currency: str
    sale_price: Decimal | None = None
    sale_status: str | None = None
    notes: str | None = None
    card: CardRead
