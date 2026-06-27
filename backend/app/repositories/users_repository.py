from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import SelfUpdate, UserCreate, UserUpdate


class UsersRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.username.asc()))
        return list(result.scalars().all())

    async def list_active_options(self) -> list[User]:
        result = await self.session.execute(
            select(User).where(User.is_active.is_(True)).order_by(User.username.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(select(User).where(func.lower(User.username) == username.lower()))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(func.lower(User.email) == email.lower()))
        return result.scalar_one_or_none()

    async def create(self, payload: UserCreate, *, must_change_password: bool = True) -> User:
        user = User(
            username=payload.username.strip(),
            full_name=payload.full_name.strip() if payload.full_name else None,
            email=payload.email.lower() if payload.email else None,
            password_hash=hash_password(payload.password),
            is_admin=payload.is_admin,
            is_active=payload.is_active,
            must_change_password=must_change_password,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, user: User, payload: UserUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)

        if "username" in data and data["username"] is not None:
            user.username = data["username"].strip()
        if "full_name" in data:
            user.full_name = data["full_name"].strip() if data["full_name"] else None
        if "email" in data:
            user.email = data["email"].lower() if data["email"] else None
        if "password" in data and data["password"]:
            user.password_hash = hash_password(data["password"])
        if "is_admin" in data and data["is_admin"] is not None:
            user.is_admin = data["is_admin"]
        if "is_active" in data and data["is_active"] is not None:
            user.is_active = data["is_active"]
        if "must_change_password" in data and data["must_change_password"] is not None:
            user.must_change_password = data["must_change_password"]
        elif "password" in data and data["password"]:
            user.must_change_password = True

        await self.session.flush()
        return user

    async def update_self(self, user: User, payload: SelfUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)

        if "username" in data and data["username"] is not None:
            user.username = data["username"].strip()
        if "full_name" in data:
            user.full_name = data["full_name"].strip() if data["full_name"] else None
        if "email" in data:
            user.email = data["email"].lower() if data["email"] else None

        await self.session.flush()
        return user

    async def accept_terms(
        self,
        user: User,
        *,
        terms_version: str,
        accepted_at,
        accepted_ip: str | None,
        accepted_user_agent: str | None,
    ) -> User:
        user.terms_version = terms_version
        user.terms_accepted_at = accepted_at
        user.terms_accepted_ip = accepted_ip
        user.terms_accepted_user_agent = accepted_user_agent
        await self.session.flush()
        return user

    async def seed_default_admin(self) -> None:
        admin = await self.get_by_username("Admin")
        if admin is None:
            self.session.add(
                User(
                    username="Admin",
                    full_name="Administrador",
                    email=None,
                    password_hash=hash_password("Admin"),
                    is_admin=True,
                    is_active=True,
                    must_change_password=True,
                )
            )
            await self.session.flush()
