from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    number: Mapped[str] = mapped_column(String(50), index=True)
    set_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    set_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    printed_total: Mapped[int | None] = mapped_column(nullable=True)
    supertype: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pokedex_number: Mapped[int | None] = mapped_column(nullable=True, index=True)
    rarity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_small: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_large: Mapped[str | None] = mapped_column(String(500), nullable=True)
    local_image_small_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    local_image_large_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_source: Mapped[str] = mapped_column(String(100), default="pokemon_tcg")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    collection_items = relationship("CollectionItem", back_populates="card")
