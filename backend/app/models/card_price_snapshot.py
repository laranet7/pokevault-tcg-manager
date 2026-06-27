from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CardPriceSnapshot(Base):
    __tablename__ = "card_price_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"), index=True)
    collection_item_id: Mapped[int] = mapped_column(ForeignKey("collection_items.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    marketplace: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    tcgplayer_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tcgplayer_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tcgplayer_price_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cardmarket_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    cardmarket_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cardmarket_price_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    finish: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_pokeball: Mapped[bool] = mapped_column(Boolean, default=False)
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    quantity: Mapped[int] = mapped_column(default=0)
    base_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    sale_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    collection = relationship("Collection")
    collection_item = relationship("CollectionItem", back_populates="price_snapshots")
    card = relationship("Card")
