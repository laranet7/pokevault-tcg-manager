import logging
import re
import unicodedata

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.cards_repository import CardsRepository
from app.repositories.collection_items_repository import CollectionItemsRepository
from app.repositories.collections_repository import CollectionsRepository
from app.schemas.card import CardUpsertPayload
from app.schemas.collection_item import (
    CollectionItemCreate,
    CollectionItemRead,
    CollectionItemsMoveRequest,
    CollectionItemsMoveResponse,
    InventorySearchResultRead,
    CollectionItemUpdate,
)
from app.schemas.pricing import PriceHistoryEntryRead
from app.services.card_media_service import CardMediaService, CardMediaServiceError
from app.services.collection_pricing_service import CollectionPricingService

router = APIRouter(tags=["collection-items"])
logger = logging.getLogger(__name__)


def _normalize_supertype(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return normalized.encode("ascii", "ignore").decode("ascii").lower()


def _sort_collection_items_for_pokedex(items: list[object]) -> list[object]:
    def sort_key(item: object) -> tuple[int, float | int, str, str]:
        card = item.card
        is_pokemon = _normalize_supertype(card.supertype) == "pokemon"
        if is_pokemon and card.pokedex_number is not None:
            return (0, card.pokedex_number, card.name.casefold(), card.number)
        if is_pokemon:
            return (1, float("inf"), card.name.casefold(), card.number)
        return (2, float("inf"), card.name.casefold(), card.number)

    return sorted(items, key=sort_key)


def _slugify_manual_value(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = normalized.encode("ascii", "ignore").decode("ascii").lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "custom"


def _build_manual_external_id(*, name: str, number: str, set_id: str | None, set_name: str | None) -> str:
    number_slug = _slugify_manual_value(number)
    if set_id:
        return f"manual:{_slugify_manual_value(set_id)}:{number_slug}"
    if set_name:
        return f"manual:{_slugify_manual_value(set_name)}:{number_slug}"
    return f"manual:{_slugify_manual_value(name)}:{number_slug}"


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


@router.post("/collections/{collection_id}/items", response_model=CollectionItemRead, status_code=status.HTTP_201_CREATED)
async def create_collection_item(
    collection_id: int,
    payload: CollectionItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionItemRead:
    items_repository = CollectionItemsRepository(db)
    collections_repository = CollectionsRepository(db)
    cards_repository = CardsRepository(db)
    media_service = CardMediaService()

    collection = await collections_repository.get_accessible_by_id(collection_id, current_user, permission="edit")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    card = await cards_repository.upsert_from_payload(payload.card)
    try:
        await media_service.ensure_local_images(card)
    except CardMediaServiceError as exc:
        logger.warning("No fue posible guardar la imagen local de %s: %s", card.external_id, exc)
    item = await items_repository.create_or_merge(collection_id=collection_id, card_id=card.id, payload=payload)
    await db.commit()
    persisted_item = await items_repository.get_by_id(item.id)
    if persisted_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado tras guardar.")
    return CollectionItemRead.model_validate(persisted_item)


@router.post("/collections/{collection_id}/items/import", response_model=CollectionItemRead, status_code=status.HTTP_201_CREATED)
async def import_collection_item(
    collection_id: int,
    external_id: str = Form(...),
    api_source: str = Form("pokemon_tcg"),
    name: str = Form(...),
    number: str = Form(...),
    set_id: str | None = Form(None),
    set_name: str | None = Form(None),
    printed_total: int | None = Form(None),
    supertype: str | None = Form(None),
    pokedex_number: int | None = Form(None),
    rarity: str | None = Form(None),
    image_small: str | None = Form(None),
    image_large: str | None = Form(None),
    quantity: int = Form(1),
    language: str | None = Form(None),
    condition: str | None = Form(None),
    finish: str | None = Form(None),
    is_pokeball: bool = Form(False),
    is_for_sale: bool = Form(False),
    base_price: str | None = Form(None),
    base_price_currency: str = Form("USD"),
    sale_margin_percent: str | None = Form(None),
    sale_price: str | None = Form(None),
    sale_status: str | None = Form("not_available"),
    notes: str | None = Form(None),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionItemRead:
    items_repository = CollectionItemsRepository(db)
    collections_repository = CollectionsRepository(db)
    cards_repository = CardsRepository(db)
    media_service = CardMediaService()

    collection = await collections_repository.get_accessible_by_id(collection_id, current_user, permission="edit")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    try:
        card_payload = CardUpsertPayload(
            external_id=external_id.strip(),
            api_source=_normalize_optional_text(api_source) or "pokemon_tcg",
            name=name.strip(),
            number=number.strip(),
            set_id=_normalize_optional_text(set_id),
            set_name=_normalize_optional_text(set_name),
            printed_total=printed_total,
            supertype=_normalize_optional_text(supertype),
            pokedex_number=pokedex_number,
            rarity=_normalize_optional_text(rarity),
            image_small=_normalize_optional_text(image_small),
            image_large=_normalize_optional_text(image_large),
        )
        payload = CollectionItemCreate(
            quantity=quantity,
            language=_normalize_optional_text(language),
            condition=_normalize_optional_text(condition),
            finish=_normalize_optional_text(finish),
            is_pokeball=is_pokeball,
            is_for_sale=is_for_sale,
            base_price=base_price,
            base_price_currency=(_normalize_optional_text(base_price_currency) or "USD").upper(),
            sale_margin_percent=sale_margin_percent,
            sale_price=sale_price,
            sale_status=_normalize_optional_text(sale_status),
            notes=_normalize_optional_text(notes),
            card=card_payload,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    card = await cards_repository.upsert_from_payload(payload.card)

    if image is not None:
        try:
            content = await image.read()
            media_service.save_uploaded_images(
                card,
                content=content,
                filename=image.filename,
                content_type=image.content_type,
            )
        except CardMediaServiceError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    else:
        try:
            await media_service.ensure_local_images(card)
        except CardMediaServiceError as exc:
            logger.warning("No fue posible guardar la imagen local de %s: %s", card.external_id, exc)

    item = await items_repository.create_or_merge(collection_id=collection_id, card_id=card.id, payload=payload)
    await db.commit()
    persisted_item = await items_repository.get_by_id(item.id)
    if persisted_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado tras guardar.")
    return CollectionItemRead.model_validate(persisted_item)


@router.post("/collections/{collection_id}/items/manual", response_model=CollectionItemRead, status_code=status.HTTP_201_CREATED)
async def create_manual_collection_item(
    collection_id: int,
    name: str = Form(...),
    number: str = Form(...),
    set_id: str | None = Form(None),
    set_name: str | None = Form(None),
    printed_total: int | None = Form(None),
    supertype: str | None = Form("Pokemon"),
    pokedex_number: int | None = Form(None),
    rarity: str | None = Form(None),
    quantity: int = Form(1),
    language: str | None = Form(None),
    condition: str | None = Form(None),
    finish: str | None = Form(None),
    is_pokeball: bool = Form(False),
    is_for_sale: bool = Form(False),
    base_price: str | None = Form(None),
    base_price_currency: str = Form("USD"),
    sale_margin_percent: str | None = Form(None),
    sale_price: str | None = Form(None),
    sale_status: str | None = Form("not_available"),
    notes: str | None = Form(None),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionItemRead:
    items_repository = CollectionItemsRepository(db)
    collections_repository = CollectionsRepository(db)
    cards_repository = CardsRepository(db)
    media_service = CardMediaService()

    collection = await collections_repository.get_accessible_by_id(collection_id, current_user, permission="edit")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    try:
        card_payload = CardUpsertPayload(
            external_id=_build_manual_external_id(name=name, number=number, set_id=set_id, set_name=set_name),
            name=name.strip(),
            number=number.strip(),
            set_id=set_id.strip() or None if set_id else None,
            set_name=set_name.strip() or None if set_name else None,
            printed_total=printed_total,
            supertype=supertype.strip() or None if supertype else None,
            pokedex_number=pokedex_number,
            rarity=rarity.strip() or None if rarity else None,
            image_small=None,
            image_large=None,
            api_source="manual",
        )
        payload = CollectionItemCreate(
            quantity=quantity,
            language=language.strip() or None if language else None,
            condition=condition.strip() or None if condition else None,
            finish=finish.strip() or None if finish else None,
            is_pokeball=is_pokeball,
            is_for_sale=is_for_sale,
            base_price=base_price,
            base_price_currency=(base_price_currency or "USD").strip().upper() or "USD",
            sale_margin_percent=sale_margin_percent,
            sale_price=sale_price,
            sale_status=sale_status.strip() or None if sale_status else None,
            notes=notes.strip() or None if notes else None,
            card=card_payload,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    card = await cards_repository.upsert_from_payload(payload.card)

    if image is not None:
        try:
            content = await image.read()
            media_service.save_uploaded_images(
                card,
                content=content,
                filename=image.filename,
                content_type=image.content_type,
            )
        except CardMediaServiceError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    item = await items_repository.create_or_merge(collection_id=collection_id, card_id=card.id, payload=payload)
    await db.commit()
    persisted_item = await items_repository.get_by_id(item.id)
    if persisted_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado tras guardar.")
    return CollectionItemRead.model_validate(persisted_item)


@router.get("/collections/{collection_id}/items", response_model=list[CollectionItemRead])
async def list_collection_items(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CollectionItemRead]:
    items_repository = CollectionItemsRepository(db)
    collections_repository = CollectionsRepository(db)
    collection = await collections_repository.get_accessible_by_id(collection_id, current_user, permission="view")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    items = await items_repository.list_by_collection(collection_id)
    if collection.sort_by_pokedex:
        items = _sort_collection_items_for_pokedex(items)
    return [CollectionItemRead.model_validate(item) for item in items]


@router.get("/collection-items/search", response_model=list[InventorySearchResultRead])
async def search_inventory_items(
    query: str = Query(..., min_length=1, description="Busqueda local en inventario por nombre, codigo o set"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InventorySearchResultRead]:
    repository = CollectionItemsRepository(db)
    results = await repository.search_inventory(query, current_user)
    return [
        InventorySearchResultRead(
            item_id=item.id,
            collection_id=collection.id,
            collection_name=collection.name,
            quantity=item.quantity,
            language=item.language,
            condition=item.condition,
            finish=item.finish,
            is_pokeball=item.is_pokeball,
            is_for_sale=item.is_for_sale,
            base_price=item.base_price,
            base_price_currency=item.base_price_currency,
            sale_price=item.sale_price,
            sale_status=item.sale_status,
            notes=item.notes,
            card=item.card,
        )
        for item, collection in results
    ]


@router.patch("/collection-items/{item_id}", response_model=CollectionItemRead)
async def update_collection_item(
    item_id: int,
    payload: CollectionItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionItemRead:
    repository = CollectionItemsRepository(db)
    collections_repository = CollectionsRepository(db)
    item = await repository.get_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado.")
    collection = await collections_repository.get_accessible_by_id(item.collection_id, current_user, permission="edit")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    updated = await repository.update(item, payload)
    await db.commit()
    persisted_item = await repository.get_by_id(updated.id)
    if persisted_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado tras actualizar.")
    return CollectionItemRead.model_validate(persisted_item)


@router.delete("/collection-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    repository = CollectionItemsRepository(db)
    collections_repository = CollectionsRepository(db)
    item = await repository.get_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado.")
    collection = await collections_repository.get_accessible_by_id(item.collection_id, current_user, permission="edit")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    await repository.delete(item)
    await db.commit()


@router.post("/collection-items/move", response_model=CollectionItemsMoveResponse)
async def move_collection_items(
    payload: CollectionItemsMoveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionItemsMoveResponse:
    repository = CollectionItemsRepository(db)
    collections_repository = CollectionsRepository(db)
    target_collection = await collections_repository.get_accessible_by_id(
        payload.target_collection_id, current_user, permission="edit"
    )
    if target_collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion destino no encontrada.")

    items = await repository.list_by_ids(payload.item_ids)
    if len(items) != len(set(payload.item_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uno o mas items no fueron encontrados.")

    moved_items = 0
    merged_items = 0

    for item in items:
        source_collection = await collections_repository.get_accessible_by_id(item.collection_id, current_user, permission="edit")
        if source_collection is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion origen no encontrada.")
        if item.collection_id == payload.target_collection_id:
            continue

        result, _ = await repository.move_to_collection(item, target_collection_id=payload.target_collection_id)
        if result == "merged":
            merged_items += 1
        else:
            moved_items += 1

    await db.commit()
    return CollectionItemsMoveResponse(
        moved_items=moved_items,
        merged_items=merged_items,
        target_collection_id=payload.target_collection_id,
    )


@router.get("/collection-items/{item_id}/price-history", response_model=list[PriceHistoryEntryRead])
async def get_collection_item_price_history(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PriceHistoryEntryRead]:
    repository = CollectionItemsRepository(db)
    collections_repository = CollectionsRepository(db)
    item = await repository.get_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado.")
    collection = await collections_repository.get_accessible_by_id(item.collection_id, current_user, permission="view")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    service = CollectionPricingService(db)
    return await service.get_collection_item_price_history(item_id)
