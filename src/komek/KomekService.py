from datetime import datetime, timedelta

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlmodel import select, or_
from fastapi import HTTPException, status
from typing import Optional
import math
from ..db.models import RequestHelp, HelpApplication, RequestStatus, ApplicationStatus, User, UserRating
from .KomekSchemas import KomekCreate, ApplyToRequestCreate, RatingRequest, UserRatingOut
from sqlalchemy import func


class KomekService:

    async def _serialize_request_with_applicant_usernames(self, request: Optional[RequestHelp], session: AsyncSession):
        if not request:
            return None

        applicant_ids = list({app.applicant_id for app in request.applications}) if request.applications else []
        username_by_id = {}
        if applicant_ids:
            users_result = await session.exec(
                select(User).where(User.id.in_(applicant_ids))
            )
            users = users_result.all()
            username_by_id = {user.id: user.username for user in users}

        return {
            "id": request.id,
            "requester_id": request.requester_id,
            "title": request.title,
            "description": request.description,
            "category": request.category,
            "status": request.status,
            "created_at": request.created_at,
            "expires_at": request.expires_at,
            "applications": [
                {
                    "id": app.id,
                    "applicant_id": app.applicant_id,
                    "applicant_username": username_by_id.get(app.applicant_id),
                    "message": app.message,
                    "status": app.status,
                    "applied_at": app.applied_at,
                }
                for app in request.applications
            ],
        }

    async def get_request(self, request_id: int, session: AsyncSession):
        result = await session.exec(
            select(RequestHelp)
            .where(RequestHelp.id == request_id)
            .options(selectinload(RequestHelp.applications))
        )
        return result.first()

    async def _get_active_involvement(self, user_id: int, session: AsyncSession):
        req_result = await session.exec(
            select(RequestHelp).where(
                RequestHelp.requester_id == user_id,
                RequestHelp.status.in_([RequestStatus.OPEN, RequestStatus.IN_PROGRESS])
            )
        )
        active_request = req_result.first()
        if active_request:
            return "requester"

        app_result = await session.exec(
            select(HelpApplication)
            .join(RequestHelp, HelpApplication.request_id == RequestHelp.id)
            .where(
                HelpApplication.applicant_id == user_id,
                HelpApplication.status == ApplicationStatus.ACCEPTED,
                RequestHelp.status.in_([RequestStatus.OPEN, RequestStatus.IN_PROGRESS]),
            )
        )
        active_help = app_result.first()
        if active_help:
            return "helper"

        return None

    async def create_request(self, user_id: int, data: KomekCreate, session: AsyncSession):
        involvement = await self._get_active_involvement(user_id, session)
        if involvement:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You are already active as a {involvement}. Finish or cancel it before creating a new request."
            )

        new_request = RequestHelp(
            requester_id=user_id,
            title=data.title,
            description=data.description,
            category=data.category,
            expires_at=datetime.utcnow() + timedelta(days=data.expires_in_days),  

        )
        session.add(new_request)
        await session.commit()
        await session.refresh(new_request)
        request = await self.get_request(new_request.id, session)
        return await self._serialize_request_with_applicant_usernames(request, session)

    

    async def get_open_requests(self, category=None, session: AsyncSession = None):
        stmt = (
            select(RequestHelp)
            .where(RequestHelp.status == RequestStatus.OPEN)
            .options(selectinload(RequestHelp.applications))
        )
        if category:
            stmt = stmt.where(RequestHelp.category == category)
        result = await session.exec(stmt)
        requests = result.all()
        serialized_requests = []
        for request in requests:
            serialized_requests.append(await self._serialize_request_with_applicant_usernames(request, session))
        return serialized_requests

    async def cancel_request(self, request_id: int, user_id: int, session: AsyncSession):
        request = await self.get_request(request_id, session)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        if request.requester_id != user_id:
            raise HTTPException(status_code=403, detail="Not your request")
        if request.status not in [RequestStatus.OPEN, RequestStatus.IN_PROGRESS]:
            raise HTTPException(status_code=400, detail="Request cannot be cancelled in its current state")
        request.status = RequestStatus.CANCELLED
        await session.commit()
        await session.refresh(request)
        request = await self.get_request(request.id, session)
        return await self._serialize_request_with_applicant_usernames(request, session)

    async def apply_to_request(self, request_id: int, applicant_id: int, data: ApplyToRequestCreate, session: AsyncSession):
        request = await self.get_request(request_id, session)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        if request.status != RequestStatus.OPEN:
            raise HTTPException(status_code=400, detail="This request is not open for applications")
        if request.requester_id == applicant_id:
            raise HTTPException(status_code=400, detail="You cannot apply to your own request")

        involvement = await self._get_active_involvement(applicant_id, session)
        if involvement:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You are already active as a {involvement}. You cannot apply to help right now."
            )
        existing = await session.exec(
            select(HelpApplication).where(
                HelpApplication.request_id == request_id,
                HelpApplication.applicant_id == applicant_id
            )
        )
        if existing.first():
            raise HTTPException(status_code=409, detail="You have already applied to this request")

        application = HelpApplication(
            request_id=request_id,
            applicant_id=applicant_id,
            message=data.message,
        )
        session.add(application)
        await session.commit()
        await session.refresh(application)
        return application

    async def accept_application(self, request_id: int, application_id: int, requester_id: int, session: AsyncSession):
        request = await self.get_request(request_id, session)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        if request.requester_id != requester_id:
            raise HTTPException(status_code=403, detail="Not your request")
        if request.status != RequestStatus.OPEN:
            raise HTTPException(status_code=400, detail="Request is not open")

        app_result = await session.exec(
            select(HelpApplication).where(
                HelpApplication.id == application_id,
                HelpApplication.request_id == request_id
            )
        )
        application = app_result.first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        application.status = ApplicationStatus.ACCEPTED
        request.status = RequestStatus.IN_PROGRESS
        await session.commit()
        await session.refresh(request)
        request = await self.get_request(request.id, session)
        return await self._serialize_request_with_applicant_usernames(request, session)

    async def reject_application(self, request_id: int, application_id: int, requester_id: int, session: AsyncSession):
        request = await self.get_request(request_id, session)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        if request.requester_id != requester_id:
            raise HTTPException(status_code=403, detail="Not your request")

        app_result = await session.exec(
            select(HelpApplication).where(
                HelpApplication.id == application_id,
                HelpApplication.request_id == request_id
            )
        )
        application = app_result.first()
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        application.status = ApplicationStatus.REJECTED
        await session.commit()
        await session.refresh(application)
        return application

    async def complete_request(self, request_id: int, requester_id: int, session: AsyncSession):
        request = await self.get_request(request_id, session)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        if request.requester_id != requester_id:
            raise HTTPException(status_code=403, detail="Not your request")
        if request.status != RequestStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Request must be in progress to complete")
        request.status = RequestStatus.COMPLETED
        await session.commit()
        await session.refresh(request)
        request = await self.get_request(request.id, session)
        return await self._serialize_request_with_applicant_usernames(request, session)

    async def get_my_requests(self, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(RequestHelp)
            .where(RequestHelp.requester_id == user_id)
            .options(selectinload(RequestHelp.applications))
        )
        requests = result.all()
        serialized_requests = []
        for request in requests:
            serialized_requests.append(await self._serialize_request_with_applicant_usernames(request, session))
        return serialized_requests

    async def get_my_applications(self, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(HelpApplication).where(HelpApplication.applicant_id == user_id)
        )
        return result.all()

    async def get_nearby_requests(self, latitude: float, longitude: float, radius_km: float, category=None, session: AsyncSession = None):
        stmt = (
            select(RequestHelp)
            .where(RequestHelp.status == RequestStatus.OPEN)
            .options(selectinload(RequestHelp.applications))
        )
        if category:
            stmt = stmt.where(RequestHelp.category == category)
        result = await session.exec(stmt)
        requests = result.all()

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            return R * 2 * math.asin(math.sqrt(a))

        nearby = []
        for req in requests:
            from sqlmodel import select as sel
            user_result = await session.exec(sel(User).where(User.id == req.requester_id))
            user = user_result.first()
            if not user or user.latitude is None or user.longitude is None:
                continue
            dist = haversine(latitude, longitude, user.latitude, user.longitude)
            if dist <= radius_km:
                nearby.append({
                    "request": req,
                    "distance_km": round(dist, 2),
                    "requester_latitude": user.latitude,
                    "requester_longitude": user.longitude,
                    "requester_username": user.username,
                })

        nearby.sort(key=lambda x: x["distance_km"])
        return nearby

    async def submit_rating(self, rater_id: int, data: RatingRequest, session: AsyncSession):
        request = await self.get_request(data.request_id, session)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        if request.status != RequestStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Request must be completed to submit rating")

        if request.requester_id != rater_id:
            raise HTTPException(status_code=403, detail="Only the requester can rate the helper")

        accepted_app = None
        for app in request.applications:
            if app.status == ApplicationStatus.ACCEPTED:
                accepted_app = app
                break
        if not accepted_app or accepted_app.applicant_id != data.target_user_id:
            raise HTTPException(status_code=400, detail="Can only rate the accepted helper")

        existing = await session.exec(
            select(UserRating).where(
                UserRating.rater_id == rater_id,
                UserRating.request_id == data.request_id
            )
        )
        if existing.first():
            raise HTTPException(status_code=409, detail="You have already rated this request")

        rating = UserRating(
            rater_id=rater_id,
            target_user_id=data.target_user_id,
            request_id=data.request_id,
            rating=data.rating,
            comment=data.comment,
        )
        session.add(rating)
        await session.commit()
        await session.refresh(rating)

        await self._update_user_average_rating(data.target_user_id, session)

        return rating

    async def _update_user_average_rating(self, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(UserRating.rating).where(UserRating.target_user_id == user_id)
        )
        ratings = result.all()
        
        if ratings:
            average_rating = float(sum(ratings)) / len(ratings)
        else:
            average_rating = 0.0
        
        user_result = await session.exec(
            select(User).where(User.id == user_id)
        )
        user = user_result.first()
        if user:
            user.rating = average_rating
            await session.commit()

    async def get_user_ratings(self, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(User).where(User.id == user_id)
        )
        user = result.first()
        if not user:
            return {"average_rating": 0.0, "total_ratings": 0}
        
        rating_count_result = await session.exec(
            select(UserRating).where(UserRating.target_user_id == user_id)
        )
        total_ratings = len(rating_count_result.all())
        
        return {
            "average_rating": user.rating,
            "total_ratings": total_ratings
        }
    
   