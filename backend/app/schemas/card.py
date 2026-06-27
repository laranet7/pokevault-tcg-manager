from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CardPrice(BaseModel):
    source: str
    currency: str
    label: str
    amount: Decimal


class CardSearchResult(BaseModel):
    external_id: str
    api_source: str = "pokemon_tcg"
    name: str
    number: str
    set_id: str | None = None
    set_name: str | None = None
    printed_total: int | None = None
    supertype: str | None = None
    pokedex_number: int | None = None
    rarity: str | None = None
    image_small: str | None = None
    image_large: str | None = None
    prices: list[CardPrice] = Field(default_factory=list)
    raw_prices: dict[str, Any] = Field(default_factory=dict)


class CardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    name: str
    number: str
    set_id: str | None = None
    set_name: str | None = None
    printed_total: int | None = None
    supertype: str | None = None
    pokedex_number: int | None = None
    rarity: str | None = None
    image_small: str | None = None
    image_large: str | None = None
    api_source: str
    created_at: datetime
    updated_at: datetime | None = None


class CardUpsertPayload(BaseModel):
    external_id: str
    name: str
    number: str
    set_id: str | None = None
    set_name: str | None = None
    printed_total: int | None = None
    supertype: str | None = None
    pokedex_number: int | None = None
    rarity: str | None = None
    image_small: str | None = None
    image_large: str | None = None
    api_source: str = "pokemon_tcg"


class CardSearchResponse(BaseModel):
    query: str
    count: int
    results: list[CardSearchResult]
