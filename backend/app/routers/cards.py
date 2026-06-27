from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.cards_repository import CardsRepository
from app.schemas.card import CardRead, CardSearchResponse
from app.services.card_media_service import CardMediaService, CardMediaServiceError
from app.services.pokemon_tcg_service import InvalidCardCodeError, PokemonTCGService, PokemonTCGServiceError

router = APIRouter(prefix="/cards", tags=["cards"])
service = PokemonTCGService()
media_service = CardMediaService()


@router.get("/search", response_model=CardSearchResponse)
async def search_cards(
    general: str | None = Query(None, description="Busqueda general por nombre o codigo"),
    code: str | None = Query(None, description="Codigo en formato number/printedTotal"),
    name: str | None = Query(None, description="Nombre o palabras clave de la carta"),
    promo_code: str | None = Query(None, description="Codigo promo en formato 088 o SVP/088"),
    promo_name: str | None = Query(None, description="Nombre de carta dentro de Scarlet & Violet Promos"),
    _: User = Depends(get_current_user),
) -> CardSearchResponse:
    try:
        provided_filters = [value for value in [general, code, name, promo_code, promo_name] if value]
        if len(provided_filters) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usa solo un filtro por vez: general, codigo, nombre, codigo promo o nombre promo.",
            )
        if general:
            query = general
            results = await service.search_general(general)
        elif code:
            query = code
            results = await service.search_by_code(code)
        elif name:
            query = name
            results = await service.search_by_name(name)
        elif promo_code:
            query = promo_code
            results = await service.search_promo_by_code(promo_code)
        elif promo_name:
            query = promo_name
            results = await service.search_promo_by_name(promo_name)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debes indicar general, codigo, nombre, codigo promo o nombre promo.",
            )
    except InvalidCardCodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PokemonTCGServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return CardSearchResponse(query=query, count=len(results), results=results)


@router.get("/{card_id}/image")
async def get_card_image(
    card_id: int,
    size: Literal["small", "large"] = Query("small"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Response:
    repository = CardsRepository(db)
    card = await repository.get_by_id(card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carta no encontrada.")

    local_path = media_service.get_local_image_path(card, size)
    if local_path and local_path.exists():
        return FileResponse(local_path, headers={"Cache-Control": "public, max-age=86400"})

    try:
        changed = await media_service.ensure_local_images(card)
        if changed:
            await db.commit()
    except CardMediaServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    local_path = media_service.get_local_image_path(card, size)
    if local_path and local_path.exists():
        return FileResponse(local_path, headers={"Cache-Control": "public, max-age=86400"})

    fallback_url = card.image_large if size == "large" else card.image_small
    fallback_url = fallback_url or card.image_large or card.image_small
    if not fallback_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La carta no tiene imagen disponible.")

    try:
        content, media_type = await media_service.download_image(fallback_url)
    except CardMediaServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return Response(content=content, media_type=media_type or "image/png", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/{card_id}", response_model=CardRead)
async def get_card(card_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> CardRead:
    repository = CardsRepository(db)
    card = await repository.get_by_id(card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carta no encontrada.")
    return CardRead.model_validate(card)
