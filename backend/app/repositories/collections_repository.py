from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.collection import Collection
from app.models.collection_item import CollectionItem
from app.models.collection_member import CollectionMember
from app.models.user import User
from app.schemas.collection import CollectionCollaboratorRole, CollectionCreate, CollectionUpdate


class CollectionsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _view_access_condition(self, current_user: User):
        if current_user.is_admin:
            return True

        membership_exists = exists(
            select(CollectionMember.id).where(
                CollectionMember.collection_id == Collection.id,
                CollectionMember.user_id == current_user.id,
            )
        )

        # Legacy collections without owner keep behaving as global collections
        # until they are assigned locally to an owner.
        return or_(
            Collection.owner_user_id == current_user.id,
            membership_exists,
            Collection.owner_user_id.is_(None),
            Collection.is_public.is_(True),
        )

    def _edit_access_condition(self, current_user: User):
        if current_user.is_admin:
            return True

        editor_exists = exists(
            select(CollectionMember.id).where(
                CollectionMember.collection_id == Collection.id,
                CollectionMember.user_id == current_user.id,
                CollectionMember.role == "editor",
            )
        )

        return or_(
            Collection.owner_user_id == current_user.id,
            editor_exists,
            Collection.owner_user_id.is_(None),
        )

    def _manage_access_condition(self, current_user: User):
        if current_user.is_admin:
            return True
        return Collection.owner_user_id == current_user.id

    def _access_condition(self, current_user: User, permission: str):
        if permission == "manage":
            return self._manage_access_condition(current_user)
        if permission == "edit":
            return self._edit_access_condition(current_user)
        return self._view_access_condition(current_user)

    async def create(self, payload: CollectionCreate, *, owner_user_id: int) -> Collection:
        collection = Collection(**payload.model_dump(), owner_user_id=owner_user_id)
        self.session.add(collection)
        await self.session.flush()
        await self.session.refresh(collection, attribute_names=["owner"])
        return collection

    async def get_by_id(self, collection_id: int) -> Collection | None:
        result = await self.session.execute(
            select(Collection)
            .options(
                selectinload(Collection.owner),
                selectinload(Collection.members).selectinload(CollectionMember.user),
            )
            .where(Collection.id == collection_id)
        )
        return result.scalar_one_or_none()

    async def get_accessible_by_id(self, collection_id: int, current_user: User, *, permission: str = "view") -> Collection | None:
        result = await self.session.execute(
            select(Collection)
            .options(
                selectinload(Collection.owner),
                selectinload(Collection.members).selectinload(CollectionMember.user),
            )
            .where(Collection.id == collection_id)
            .where(self._access_condition(current_user, permission))
        )
        return result.scalar_one_or_none()

    async def list_accessible(self, current_user: User, *, permission: str = "view") -> list[tuple[Collection, int, int]]:
        statement = (
            select(
                Collection,
                func.count(CollectionItem.id).label("items_count"),
                func.coalesce(func.sum(CollectionItem.quantity), 0).label("total_quantity"),
            )
            .options(
                selectinload(Collection.owner),
                selectinload(Collection.members).selectinload(CollectionMember.user),
            )
            .outerjoin(CollectionItem, CollectionItem.collection_id == Collection.id)
            .where(self._access_condition(current_user, permission))
            .group_by(Collection.id)
            .order_by(Collection.name.asc())
        )
        result = await self.session.execute(statement)
        return list(result.unique().all())

    async def list_accessible_ids(self, current_user: User, *, permission: str = "view") -> list[int]:
        result = await self.session.execute(
            select(Collection.id).where(self._access_condition(current_user, permission)).order_by(Collection.id.asc())
        )
        return list(result.scalars().all())

    async def get_with_counts(self, collection_id: int, current_user: User, *, permission: str = "view") -> tuple[Collection, int, int] | None:
        statement = (
            select(
                Collection,
                func.count(CollectionItem.id).label("items_count"),
                func.coalesce(func.sum(CollectionItem.quantity), 0).label("total_quantity"),
            )
            .options(
                selectinload(Collection.owner),
                selectinload(Collection.members).selectinload(CollectionMember.user),
            )
            .outerjoin(CollectionItem, CollectionItem.collection_id == Collection.id)
            .where(Collection.id == collection_id)
            .where(self._access_condition(current_user, permission))
            .group_by(Collection.id)
        )
        result = await self.session.execute(statement)
        return result.unique().first()

    async def exists_by_name(self, name: str, *, exclude_id: int | None = None) -> bool:
        statement = select(Collection.id).where(func.lower(Collection.name) == name.lower())
        if exclude_id is not None:
            statement = statement.where(Collection.id != exclude_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def update(self, collection: Collection, payload: CollectionUpdate) -> Collection:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(collection, field, value)

        await self.session.flush()
        await self.session.refresh(collection, attribute_names=["owner"])
        return collection

    async def list_members(self, collection_id: int) -> list[CollectionMember]:
        result = await self.session.execute(
            select(CollectionMember)
            .options(selectinload(CollectionMember.user))
            .where(CollectionMember.collection_id == collection_id)
            .order_by(CollectionMember.role.asc(), CollectionMember.created_at.asc(), CollectionMember.id.asc())
        )
        return list(result.scalars().all())

    async def get_member(self, collection_id: int, user_id: int) -> CollectionMember | None:
        result = await self.session.execute(
            select(CollectionMember)
            .options(selectinload(CollectionMember.user))
            .where(CollectionMember.collection_id == collection_id, CollectionMember.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_member(self, *, collection_id: int, user_id: int, role: CollectionCollaboratorRole) -> CollectionMember:
        member = await self.get_member(collection_id, user_id)
        if member is None:
            member = CollectionMember(collection_id=collection_id, user_id=user_id, role=role)
            self.session.add(member)
        else:
            member.role = role

        await self.session.flush()
        await self.session.refresh(member, attribute_names=["user"])
        return member

    async def delete_member(self, member: CollectionMember) -> None:
        await self.session.delete(member)

    async def transfer_ownership(self, collection: Collection, *, new_owner: User, previous_owner_role: str = "editor") -> Collection:
        previous_owner_id = collection.owner_user_id
        if previous_owner_id and previous_owner_id != new_owner.id:
            await self.upsert_member(
                collection_id=collection.id,
                user_id=previous_owner_id,
                role=previous_owner_role,  # type: ignore[arg-type]
            )

        current_member = await self.get_member(collection.id, new_owner.id)
        if current_member is not None:
            await self.delete_member(current_member)

        collection.owner_user_id = new_owner.id
        await self.session.flush()
        await self.session.refresh(collection, attribute_names=["owner"])
        return collection

    async def delete(self, collection: Collection) -> None:
        await self.session.delete(collection)
