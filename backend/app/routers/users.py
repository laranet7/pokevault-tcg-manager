from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_admin_user, get_current_user
from app.models.user import User
from app.repositories.users_repository import UsersRepository
from app.schemas.user import SelfUpdate, UserCreate, UserOptionRead, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


async def _ensure_unique_fields(
    repository: UsersRepository,
    *,
    username: str | None = None,
    email: str | None = None,
    exclude_user_id: int | None = None,
) -> None:
    if username:
        existing = await repository.get_by_username(username)
        if existing is not None and existing.id != exclude_user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese nombre.")

    if email:
        existing_email = await repository.get_by_email(email)
        if existing_email is not None and existing_email.id != exclude_user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese email.")


@router.get("", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> list[UserRead]:
    repository = UsersRepository(db)
    users = await repository.list_all()
    return [UserRead.model_validate(user) for user in users]


@router.get("/options", response_model=list[UserOptionRead])
async def list_user_options(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[UserOptionRead]:
    repository = UsersRepository(db)
    users = await repository.list_active_options()
    return [UserOptionRead.model_validate(user) for user in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> UserRead:
    repository = UsersRepository(db)
    await _ensure_unique_fields(repository, username=payload.username, email=payload.email)
    user = await repository.create(payload, must_change_password=True)
    await db.commit()
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: SelfUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    repository = UsersRepository(db)
    await _ensure_unique_fields(repository, username=payload.username, email=payload.email, exclude_user_id=current_user.id)
    user = await repository.update_self(current_user, payload)
    await db.commit()
    await db.refresh(user)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    repository = UsersRepository(db)
    user = await repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    is_self = current_user.id == user.id
    if not current_user.is_admin and not is_self:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes modificar este usuario.")

    if not current_user.is_admin:
        forbidden_fields = {"password", "is_admin", "is_active", "must_change_password"}
        provided_forbidden = forbidden_fields.intersection(payload.model_dump(exclude_unset=True).keys())
        if provided_forbidden:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Actualizacion no permitida.")

    await _ensure_unique_fields(repository, username=payload.username, email=payload.email, exclude_user_id=user.id)
    updated = await repository.update(user, payload)
    await db.commit()
    await db.refresh(updated)
    return UserRead.model_validate(updated)
