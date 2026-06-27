from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.users_repository import UsersRepository
from app.schemas.terms import AcceptTermsRequest, AcceptTermsResponse, TermsStatusRead

router = APIRouter(prefix="/me", tags=["me"])


def _build_terms_status(user: User) -> TermsStatusRead:
    settings = get_settings()
    accepted = bool(user.terms_accepted_at and user.terms_version == settings.terms_version)
    return TermsStatusRead(
        accepted=accepted,
        current_version=settings.terms_version,
        accepted_version=user.terms_version,
        accepted_at=user.terms_accepted_at,
    )


@router.get("/terms-status", response_model=TermsStatusRead)
async def terms_status(current_user: User = Depends(get_current_user)) -> TermsStatusRead:
    return _build_terms_status(current_user)


@router.post("/accept-terms", response_model=AcceptTermsResponse)
async def accept_terms(
    payload: AcceptTermsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AcceptTermsResponse:
    settings = get_settings()
    if payload.terms_version != settings.terms_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La version de terminos enviada no coincide con la version vigente.",
        )

    if current_user.terms_accepted_at and current_user.terms_version == settings.terms_version:
        return AcceptTermsResponse(
            accepted=True,
            terms_version=current_user.terms_version,
            accepted_at=current_user.terms_accepted_at,
        )

    repository = UsersRepository(db)
    accepted_ip = request.client.host if request.client else None
    accepted_user_agent = request.headers.get("user-agent")
    accepted_at = datetime.now(timezone.utc)

    user = await repository.accept_terms(
        current_user,
        terms_version=settings.terms_version,
        accepted_at=accepted_at,
        accepted_ip=accepted_ip,
        accepted_user_agent=accepted_user_agent,
    )
    await db.commit()
    await db.refresh(user)

    return AcceptTermsResponse(
        accepted=True,
        terms_version=user.terms_version or settings.terms_version,
        accepted_at=user.terms_accepted_at or accepted_at,
    )
