from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from ..db.main import get_session
from ..users.dependencies import get_current_user
from ..db.models import User, HelpCategory
from .KomekSchemas import KomekCreate, KomekOut, ApplyToRequestCreate, KomekNearbyOut, RatingRequest, UserRatingOut
from .KomekService import KomekService

komek_router = APIRouter()
service = KomekService()


@komek_router.post("/requests", response_model=KomekOut, status_code=201)
async def create_request(
    data: KomekCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await service.create_request(current_user.id, data, session)


@komek_router.get("/requests", response_model=list[KomekOut])
async def list_open_requests(
    category: Optional[HelpCategory] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await service.get_open_requests(category=category, session=session)


@komek_router.get("/requests/me", response_model=list[KomekOut])
async def my_requests(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await service.get_my_requests(current_user.id, session)


@komek_router.get("/requests/me/applications")
async def my_applications(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await service.get_my_applications(current_user.id, session)


@komek_router.get("/requests/{request_id}", response_model=KomekOut)
async def get_request(
    request_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from fastapi import HTTPException
    req = await service.get_request(request_id, session)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


@komek_router.delete("/requests/{request_id}/cancel", response_model=KomekOut)
async def cancel_request(
    request_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await service.cancel_request(request_id, current_user.id, session)


@komek_router.post("/requests/{request_id}/apply")
async def apply_to_request(
    request_id: int,
    data: ApplyToRequestCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await service.apply_to_request(request_id, current_user.id, data, session)


@komek_router.post("/requests/{request_id}/applications/{application_id}/accept", response_model=KomekOut)
async def accept_application(
    request_id: int,
    application_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await service.accept_application(request_id, application_id, current_user.id, session)


@komek_router.post("/requests/{request_id}/applications/{application_id}/reject")
async def reject_application(
    request_id: int,
    application_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await service.reject_application(request_id, application_id, current_user.id, session)


@komek_router.post("/requests/{request_id}/complete", response_model=KomekOut)
async def complete_request(
    request_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await service.complete_request(request_id, current_user.id, session)

@komek_router.get("/requests/nearby",response_model=list[KomekNearbyOut])
async def get_nearby_requests(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=20.0, gt=0, le=500),
    category: Optional[HelpCategory] = Query(default=None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    
):
    return await service.get_nearby_requests(latitude, longitude, radius_km, category, session)


@komek_router.post("/ratings", response_model=UserRatingOut, status_code=201)
async def submit_rating(
    data: RatingRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await service.submit_rating(current_user.id, data, session)


@komek_router.get("/users/{user_id}/ratings", response_model=list[UserRatingOut])
async def get_user_ratings(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await service.get_user_ratings(user_id, session)