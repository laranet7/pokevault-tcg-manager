from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(default=1)
    language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    finish: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pattern_variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_for_sale: Mapped[bool] = mapped_column(Boolean, default=False)
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    base_price_currency: Mapped[str] = mapped_column(String(10), default="USD")
    tcgplayer_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    tcgplayer_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tcgplayer_price_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cardmarket_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    cardmarket_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cardmarket_price_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sale_margin_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    sale_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    collection = relationship("Collection", back_populates="items")
    card = relationship("Card", back_populates="collection_items")
    price_snapshots = relationship("CardPriceSnapshot", back_populates="collection_item", cascade="all, delete-orphan")
