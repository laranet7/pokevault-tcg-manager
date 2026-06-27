from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.pricing import CollectionValuationRead, DashboardPriceMoversRead
from app.services.collection_pricing_service import CollectionPricingService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/collections-valuation", response_model=list[CollectionValuationRead])
async def get_collections_valuation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CollectionValuationRead]:
    service = CollectionPricingService(db)
    return await service.get_collections_valuation(current_user)


@router.get("/price-movers", response_model=DashboardPriceMoversRead)
async def get_dashboard_price_movers(
    days: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardPriceMoversRead:
    service = CollectionPricingService(db)
    return await service.get_dashboard_price_movers(current_user, days=days, limit=5)
