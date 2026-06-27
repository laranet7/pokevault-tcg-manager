from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.repositories.users_repository import UsersRepository
from app.routers import auth, cards, collection_items, collections, dashboard, health, me, users
from app.services.card_media_service import CardMediaService

settings = get_settings()


async def _seed(session: AsyncSession) -> None:
    users_repository = UsersRepository(session)
    if settings.seed_default_admin:
        await users_repository.seed_default_admin()
    await session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    CardMediaService().ensure_storage_dirs()
    if settings.seed_default_admin:
        async with AsyncSessionLocal() as session:
            await _seed(session)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(me.router, prefix=settings.api_prefix)
app.include_router(cards.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(collections.router, prefix=settings.api_prefix)
app.include_router(collection_items.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
