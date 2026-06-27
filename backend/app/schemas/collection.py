from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserOptionRead

CollectionCollaboratorRole = Literal["viewer", "editor"]
CollectionAccessRole = Literal["owner", "viewer", "editor"]


class CollectionCreate(BaseModel):
    name: str
    description: str | None = None
    type: str | None = None
    is_public: bool = False
    sort_by_pokedex: bool = False


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None
    is_public: bool | None = None
    sort_by_pokedex: bool | None = None


class CollectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    type: str | None = None
    is_public: bool
    sort_by_pokedex: bool
    owner_user_id: int | None = None
    owner: UserOptionRead | None = None
    created_at: datetime
    updated_at: datetime | None = None
    items_count: int = 0
    total_quantity: int = 0
    current_user_role: CollectionAccessRole | None = None
    can_edit: bool = False
    can_manage: bool = False


class CollectionCollaboratorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    role: CollectionCollaboratorRole
    created_at: datetime
    updated_at: datetime | None = None
    user: UserOptionRead


class CollectionCollaboratorUpsert(BaseModel):
    user_id: int = Field(ge=1)
    role: CollectionCollaboratorRole


class CollectionOwnershipTransfer(BaseModel):
    user_id: int = Field(ge=1)
