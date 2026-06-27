from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_price_snapshot import CardPriceSnapshot


class CardPriceSnapshotsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        collection_id: int,
        collection_item_id: int,
        card_id: int,
        source: str | None,
        marketplace: str | None,
        currency: str,
        tcgplayer_price: Decimal | None,
        tcgplayer_currency: str | None,
        tcgplayer_price_label: str | None,
        cardmarket_price: Decimal | None,
        cardmarket_currency: str | None,
        cardmarket_price_label: str | None,
        finish: str | None,
        is_pokeball: bool,
        base_price: Decimal | None,
        sale_price: Decimal | None,
        quantity: int,
        base_total: Decimal | None,
        sale_total: Decimal | None,
        captured_at: datetime,
        raw_payload_json: str | None,
    ) -> CardPriceSnapshot:
        snapshot = CardPriceSnapshot(
            collection_id=collection_id,
            collection_item_id=collection_item_id,
            card_id=card_id,
            source=source,
            marketplace=marketplace,
            currency=currency,
            tcgplayer_price=tcgplayer_price,
            tcgplayer_currency=tcgplayer_currency,
            tcgplayer_price_label=tcgplayer_price_label,
            cardmarket_price=cardmarket_price,
            cardmarket_currency=cardmarket_currency,
            cardmarket_price_label=cardmarket_price_label,
            finish=finish,
            is_pokeball=is_pokeball,
            base_price=base_price,
            sale_price=sale_price,
            quantity=quantity,
            base_total=base_total,
            sale_total=sale_total,
            captured_at=captured_at,
            raw_payload_json=raw_payload_json,
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def list_by_collection_item(self, collection_item_id: int) -> list[CardPriceSnapshot]:
        result = await self.session.execute(
            select(CardPriceSnapshot)
            .where(CardPriceSnapshot.collection_item_id == collection_item_id)
            .order_by(CardPriceSnapshot.captured_at.asc(), CardPriceSnapshot.id.asc())
        )
        return list(result.scalars().all())

    async def list_by_collection(self, collection_id: int) -> list[CardPriceSnapshot]:
        result = await self.session.execute(
            select(CardPriceSnapshot)
            .where(CardPriceSnapshot.collection_id == collection_id)
            .order_by(CardPriceSnapshot.collection_item_id.asc(), CardPriceSnapshot.captured_at.asc(), CardPriceSnapshot.id.asc())
        )
        return list(result.scalars().all())

    async def list_by_collection_items(self, collection_item_ids: list[int]) -> list[CardPriceSnapshot]:
        if not collection_item_ids:
            return []

        result = await self.session.execute(
            select(CardPriceSnapshot)
            .where(CardPriceSnapshot.collection_item_id.in_(collection_item_ids))
            .order_by(CardPriceSnapshot.collection_item_id.asc(), CardPriceSnapshot.captured_at.asc(), CardPriceSnapshot.id.asc())
        )
        return list(result.scalars().all())

    async def list_collection_capture_summaries(
        self, collection_ids: list[int] | None = None
    ) -> list[tuple[int, datetime, Decimal, Decimal]]:
        statement = (
            select(
                CardPriceSnapshot.collection_id,
                CardPriceSnapshot.captured_at,
                func.coalesce(func.sum(CardPriceSnapshot.base_total), 0),
                func.coalesce(func.sum(CardPriceSnapshot.sale_total), 0),
            )
            .group_by(CardPriceSnapshot.collection_id, CardPriceSnapshot.captured_at)
            .order_by(CardPriceSnapshot.collection_id.asc(), CardPriceSnapshot.captured_at.asc())
        )
        if collection_ids is not None:
            if not collection_ids:
                return []
            statement = statement.where(CardPriceSnapshot.collection_id.in_(collection_ids))

        result = await self.session.execute(statement)
        return list(result.all())
