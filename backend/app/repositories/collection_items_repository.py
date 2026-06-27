from decimal import Decimal, ROUND_HALF_UP

import re

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.card import Card
from app.models.collection import Collection
from app.models.collection_item import CollectionItem
from app.models.collection_member import CollectionMember
from app.models.user import User
from app.schemas.collection_item import CollectionItemCreate, CollectionItemUpdate

CARD_CODE_REGEX = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")
PROMO_CODE_REGEX = re.compile(r"^\s*([A-Za-z]{2,10})\s*/\s*(\d+)\s*$")
SPECIAL_CARD_CODE_REGEX = re.compile(r"^\s*([A-Za-z]{1,5}\d{1,3})\s*/\s*([A-Za-z]{0,5}\d{1,3})\s*$")
SET_LOCAL_ID_REFERENCE_REGEX = re.compile(r"^\s*([A-Za-z]{2,6})\s+(\d{1,3})\s*$")
ALPHANUMERIC_NUMBER_REGEX = re.compile(r"^[A-Za-z]{1,5}\d{1,3}$")


class CollectionItemsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_collection(self, collection_id: int) -> Collection | None:
        result = await self.session.execute(select(Collection).where(Collection.id == collection_id))
        return result.scalar_one_or_none()

    async def find_matching_item(
        self,
        *,
        collection_id: int,
        card_id: int,
        payload: CollectionItemCreate,
    ) -> CollectionItem | None:
        result = await self.session.execute(
            select(CollectionItem)
            .options(selectinload(CollectionItem.card))
            .where(CollectionItem.collection_id == collection_id)
            .where(CollectionItem.card_id == card_id)
            .where(CollectionItem.language == payload.language)
            .where(CollectionItem.condition == payload.condition)
            .where(CollectionItem.finish == payload.finish)
            .where(CollectionItem.is_pokeball == payload.is_pokeball)
        )
        return result.scalar_one_or_none()

    async def create(self, collection_id: int, card_id: int, payload: CollectionItemCreate) -> CollectionItem:
        item = CollectionItem(collection_id=collection_id, card_id=card_id, **payload.model_dump(exclude={"card"}))
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item, attribute_names=["card"])
        return item

    async def create_or_merge(self, collection_id: int, card_id: int, payload: CollectionItemCreate) -> CollectionItem:
        existing_item = await self.find_matching_item(collection_id=collection_id, card_id=card_id, payload=payload)

        if existing_item is None:
            return await self.create(collection_id=collection_id, card_id=card_id, payload=payload)

        existing_item.quantity += payload.quantity
        existing_item.is_pokeball = payload.is_pokeball
        existing_item.is_for_sale = payload.is_for_sale
        existing_item.base_price = payload.base_price
        existing_item.base_price_currency = payload.base_price_currency
        existing_item.tcgplayer_price = None
        existing_item.tcgplayer_currency = None
        existing_item.tcgplayer_price_label = None
        existing_item.cardmarket_price = None
        existing_item.cardmarket_currency = None
        existing_item.cardmarket_price_label = None
        existing_item.sale_margin_percent = payload.sale_margin_percent
        existing_item.sale_price = payload.sale_price
        existing_item.sale_status = payload.sale_status
        existing_item.notes = payload.notes

        await self.session.flush()
        await self.session.refresh(existing_item, attribute_names=["card"])
        return existing_item

    async def list_by_collection(self, collection_id: int) -> list[CollectionItem]:
        result = await self.session.execute(
            select(CollectionItem)
            .options(selectinload(CollectionItem.card))
            .where(CollectionItem.collection_id == collection_id)
            .order_by(CollectionItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def search_inventory(self, query: str, current_user: User) -> list[tuple[CollectionItem, Collection]]:
        normalized_query = " ".join(query.strip().split())
        if not normalized_query:
            return []

        if current_user.is_admin:
            access_filter = True
        else:
            membership_exists = (
                select(CollectionMember.id)
                .where(
                    CollectionMember.collection_id == Collection.id,
                    CollectionMember.user_id == current_user.id,
                )
                .exists()
            )
            access_filter = or_(
                Collection.owner_user_id == current_user.id,
                membership_exists,
                Collection.owner_user_id.is_(None),
                Collection.is_public.is_(True),
            )

        statement = (
            select(CollectionItem, Collection)
            .join(Collection, CollectionItem.collection_id == Collection.id)
            .join(Card, CollectionItem.card_id == Card.id)
            .options(selectinload(CollectionItem.card))
            .where(access_filter)
            .where(self._build_inventory_filter(normalized_query))
            .order_by(Card.name.asc(), Collection.name.asc(), CollectionItem.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.all())

    async def get_by_id(self, item_id: int) -> CollectionItem | None:
        result = await self.session.execute(
            select(CollectionItem).options(selectinload(CollectionItem.card)).where(CollectionItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def list_by_ids(self, item_ids: list[int]) -> list[CollectionItem]:
        result = await self.session.execute(
            select(CollectionItem)
            .options(selectinload(CollectionItem.card))
            .where(CollectionItem.id.in_(item_ids))
        )
        return list(result.scalars().all())

    async def find_matching_existing_item(
        self,
        *,
        collection_id: int,
        item: CollectionItem,
        exclude_item_id: int | None = None,
    ) -> CollectionItem | None:
        statement = (
            select(CollectionItem)
            .options(selectinload(CollectionItem.card))
            .where(CollectionItem.collection_id == collection_id)
            .where(CollectionItem.card_id == item.card_id)
            .where(CollectionItem.language == item.language)
            .where(CollectionItem.condition == item.condition)
            .where(CollectionItem.finish == item.finish)
            .where(CollectionItem.is_pokeball == item.is_pokeball)
        )
        if exclude_item_id is not None:
            statement = statement.where(CollectionItem.id != exclude_item_id)

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def update(self, item: CollectionItem, payload: CollectionItemUpdate) -> CollectionItem:
        data = payload.model_dump(exclude_unset=True)

        for field, value in data.items():
            setattr(item, field, value)

        if ("sale_price" not in data or data.get("sale_price") is None) and item.base_price is not None and item.sale_margin_percent is not None:
            multiplier = Decimal("1") + (item.sale_margin_percent / Decimal("100"))
            item.sale_price = (item.base_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        await self.session.flush()
        await self.session.refresh(item, attribute_names=["card"])
        return item

    async def move_to_collection(self, item: CollectionItem, *, target_collection_id: int) -> tuple[str, CollectionItem]:
        existing_target_item = await self.find_matching_existing_item(
            collection_id=target_collection_id,
            item=item,
            exclude_item_id=item.id,
        )

        if existing_target_item is None:
            item.collection_id = target_collection_id
            await self.session.flush()
            await self.session.refresh(item, attribute_names=["card"])
            return ("moved", item)

        existing_target_item.quantity += item.quantity
        existing_target_item.is_for_sale = item.is_for_sale
        existing_target_item.base_price = item.base_price
        existing_target_item.base_price_currency = item.base_price_currency
        existing_target_item.tcgplayer_price = item.tcgplayer_price
        existing_target_item.tcgplayer_currency = item.tcgplayer_currency
        existing_target_item.tcgplayer_price_label = item.tcgplayer_price_label
        existing_target_item.cardmarket_price = item.cardmarket_price
        existing_target_item.cardmarket_currency = item.cardmarket_currency
        existing_target_item.cardmarket_price_label = item.cardmarket_price_label
        existing_target_item.sale_margin_percent = item.sale_margin_percent
        existing_target_item.sale_price = item.sale_price
        existing_target_item.sale_status = item.sale_status
        existing_target_item.notes = item.notes or existing_target_item.notes

        if existing_target_item.sale_price is None and existing_target_item.base_price is not None and existing_target_item.sale_margin_percent is not None:
            multiplier = Decimal("1") + (existing_target_item.sale_margin_percent / Decimal("100"))
            existing_target_item.sale_price = (existing_target_item.base_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        await self.session.delete(item)
        await self.session.flush()
        await self.session.refresh(existing_target_item, attribute_names=["card"])
        return ("merged", existing_target_item)

    async def delete(self, item: CollectionItem) -> None:
        await self.session.delete(item)

    def _build_inventory_filter(self, query: str):
        upper_query = query.upper()

        card_code_match = CARD_CODE_REGEX.fullmatch(query)
        if card_code_match:
            left = self._number_candidates(card_code_match.group(1))
            printed_total = int(card_code_match.group(2))
            return and_(Card.number.in_(left), Card.printed_total == printed_total)

        promo_match = PROMO_CODE_REGEX.fullmatch(upper_query)
        if promo_match:
            prefix = promo_match.group(1).lower()
            number_candidates = self._number_candidates(promo_match.group(2))
            return and_(Card.set_id == prefix, Card.number.in_(number_candidates))

        special_card_match = SPECIAL_CARD_CODE_REGEX.fullmatch(upper_query)
        if special_card_match:
            number = special_card_match.group(1).upper()
            printed_total = int(re.sub(r"\D", "", special_card_match.group(2)))
            return and_(Card.number == number, Card.printed_total == printed_total)

        set_local_match = SET_LOCAL_ID_REFERENCE_REGEX.fullmatch(upper_query)
        if set_local_match:
            set_id = set_local_match.group(1).lower()
            number_candidates = self._number_candidates(set_local_match.group(2))
            return and_(Card.set_id == set_id, Card.number.in_(number_candidates))

        if ALPHANUMERIC_NUMBER_REGEX.fullmatch(upper_query):
            return Card.number == upper_query

        tokens = [token for token in query.split(" ") if token]
        token_filters = []
        for token in tokens:
            token_filters.append(
                or_(
                    Card.name.ilike(f"%{token}%"),
                    Card.number.ilike(f"%{token}%"),
                    Card.set_name.ilike(f"%{token}%"),
                    Card.set_id.ilike(f"%{token}%"),
                    Collection.name.ilike(f"%{token}%"),
                )
            )

        return and_(*token_filters)

    def _number_candidates(self, value: str) -> list[str]:
        digits_only = re.sub(r"\D", "", value)
        if not digits_only:
            return [value]

        normalized = str(int(digits_only))
        padded = digits_only.zfill(3)
        candidates = [normalized]
        if padded not in candidates:
            candidates.append(padded)
        return candidates
