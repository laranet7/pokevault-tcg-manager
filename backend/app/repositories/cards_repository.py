from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.schemas.card import CardUpsertPayload


class CardsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, card_id: int) -> Card | None:
        result = await self.session.execute(select(Card).where(Card.id == card_id))
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_id: str) -> Card | None:
        result = await self.session.execute(select(Card).where(Card.external_id == external_id))
        return result.scalar_one_or_none()

    async def upsert_from_payload(self, payload: CardUpsertPayload) -> Card:
        card = await self.get_by_external_id(payload.external_id)

        if card is None:
            card = Card(**payload.model_dump())
            self.session.add(card)
            await self.session.flush()
            return card

        for field, value in payload.model_dump().items():
            setattr(card, field, value)

        await self.session.flush()
        return card
