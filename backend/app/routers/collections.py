from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.collections_repository import CollectionsRepository
from app.repositories.users_repository import UsersRepository
from app.schemas.collection import (
    CollectionCollaboratorRead,
    CollectionCollaboratorUpsert,
    CollectionCreate,
    CollectionOwnershipTransfer,
    CollectionRead,
    CollectionUpdate,
)
from app.schemas.pricing import CollectionPriceVariationRead, CollectionRefreshPricesResponse
from app.services.collection_pricing_service import CollectionPricingService
from app.services.pokemon_tcg_service import PokemonTCGServiceError

router = APIRouter(prefix="/collections", tags=["collections"])


def _resolve_role(collection, current_user: User) -> str | None:
    if current_user.is_admin:
        return "owner"
    if collection.owner_user_id == current_user.id:
        return "owner"

    for member in collection.members:
        if member.user_id == current_user.id:
            return member.role
    return None


def _serialize_collection(payload: tuple, current_user: User) -> CollectionRead:
    collection, items_count, total_quantity = payload
    role = _resolve_role(collection, current_user)
    return CollectionRead.model_validate(collection).model_copy(
        update={
            "items_count": items_count,
            "total_quantity": total_quantity,
            "current_user_role": role,
            "can_edit": role in {"owner", "editor"} or current_user.is_admin or collection.owner_user_id is None,
            "can_manage": role == "owner" or current_user.is_admin,
        }
    )


@router.post("", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
async def create_collection(
    payload: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionRead:
    repository = CollectionsRepository(db)

    if await repository.exists_by_name(payload.name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una coleccion con ese nombre.")

    collection = await repository.create(payload, owner_user_id=current_user.id)
    await db.commit()
    return CollectionRead.model_validate(collection).model_copy(
        update={"current_user_role": "owner", "can_edit": True, "can_manage": True}
    )


@router.get("", response_model=list[CollectionRead])
async def list_collections(
    permission: Literal["view", "edit", "manage"] = Query("view"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CollectionRead]:
    repository = CollectionsRepository(db)
    collections = await repository.list_accessible(current_user, permission=permission)
    return [_serialize_collection(payload, current_user) for payload in collections]


@router.get("/{collection_id}", response_model=CollectionRead)
async def get_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionRead:
    repository = CollectionsRepository(db)
    collection = await repository.get_with_counts(collection_id, current_user, permission="view")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")
    return _serialize_collection(collection, current_user)


@router.patch("/{collection_id}", response_model=CollectionRead)
async def update_collection(
    collection_id: int,
    payload: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionRead:
    repository = CollectionsRepository(db)
    collection = await repository.get_accessible_by_id(collection_id, current_user, permission="manage")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    if payload.name and await repository.exists_by_name(payload.name, exclude_id=collection_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una coleccion con ese nombre.")

    await repository.update(collection, payload)
    await db.commit()

    updated = await repository.get_with_counts(collection_id, current_user, permission="view")
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")
    return _serialize_collection(updated, current_user)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    repository = CollectionsRepository(db)
    collection = await repository.get_accessible_by_id(collection_id, current_user, permission="manage")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    await repository.delete(collection)
    await db.commit()


@router.post("/{collection_id}/refresh-prices", response_model=CollectionRefreshPricesResponse)
async def refresh_collection_prices(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionRefreshPricesResponse:
    repository = CollectionsRepository(db)
    collection = await repository.get_accessible_by_id(collection_id, current_user, permission="edit")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    service = CollectionPricingService(db)
    try:
        response = await service.refresh_collection_prices(collection_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PokemonTCGServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    await db.commit()
    return response


@router.get("/{collection_id}/price-variation", response_model=CollectionPriceVariationRead)
async def get_collection_price_variation(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionPriceVariationRead:
    repository = CollectionsRepository(db)
    collection = await repository.get_accessible_by_id(collection_id, current_user, permission="view")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    service = CollectionPricingService(db)
    try:
        return await service.get_collection_price_variation(collection_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{collection_id}/collaborators", response_model=list[CollectionCollaboratorRead])
async def list_collection_collaborators(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CollectionCollaboratorRead]:
    repository = CollectionsRepository(db)
    collection = await repository.get_accessible_by_id(collection_id, current_user, permission="manage")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    members = await repository.list_members(collection_id)
    return [CollectionCollaboratorRead.model_validate(member) for member in members]


@router.post("/{collection_id}/collaborators", response_model=CollectionCollaboratorRead)
async def upsert_collection_collaborator(
    collection_id: int,
    payload: CollectionCollaboratorUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionCollaboratorRead:
    collections_repository = CollectionsRepository(db)
    users_repository = UsersRepository(db)

    collection = await collections_repository.get_accessible_by_id(collection_id, current_user, permission="manage")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    if collection.owner_user_id == payload.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario owner no puede agregarse como colaborador.")

    user = await users_repository.get_by_id(payload.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario colaborador no encontrado.")

    member = await collections_repository.upsert_member(
        collection_id=collection_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    await db.commit()
    await db.refresh(member)
    return CollectionCollaboratorRead.model_validate(member)


@router.delete("/{collection_id}/collaborators/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection_collaborator(
    collection_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    repository = CollectionsRepository(db)
    collection = await repository.get_accessible_by_id(collection_id, current_user, permission="manage")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    if collection.owner_user_id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes quitar al usuario owner desde colaboradores.")

    member = await repository.get_member(collection_id, user_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Colaborador no encontrado.")

    await repository.delete_member(member)
    await db.commit()


@router.post("/{collection_id}/transfer-ownership", response_model=CollectionRead)
async def transfer_collection_ownership(
    collection_id: int,
    payload: CollectionOwnershipTransfer,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionRead:
    collections_repository = CollectionsRepository(db)
    users_repository = UsersRepository(db)
    collection = await collections_repository.get_accessible_by_id(collection_id, current_user, permission="manage")
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")

    if collection.owner_user_id is None and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede transferir una coleccion sin owner.")

    target_user = await users_repository.get_by_id(payload.user_id)
    if target_user is None or not target_user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario destino no encontrado.")

    member = await collections_repository.get_member(collection_id, payload.user_id)
    if member is None or member.role != "editor":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nuevo owner debe ser un colaborador con rol editor.")

    await collections_repository.transfer_ownership(collection, new_owner=target_user)
    await db.commit()

    updated = await collections_repository.get_with_counts(collection_id, current_user, permission="view")
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coleccion no encontrada.")
    return _serialize_collection(updated, current_user)
