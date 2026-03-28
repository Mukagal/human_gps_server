from datetime import datetime, timedelta

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlmodel import select, or_
from fastapi import HTTPException, status
from typing import Optional

from ..db.models import RequestHelp, HelpApplication, RequestStatus, ApplicationStatus
from .KomekSchemas import KomekCreate, ApplyToRequestCreate


class KomekService:

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
            select(HelpApplication).where(
                HelpApplication.applicant_id == user_id,
                HelpApplication.status == ApplicationStatus.ACCEPTED
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
        return await self.get_request(new_request.id, session)

    

    async def get_open_requests(self, category=None, session: AsyncSession = None):
        stmt = (
            select(RequestHelp)
            .where(RequestHelp.status == RequestStatus.OPEN)
            .options(selectinload(RequestHelp.applications))
        )
        if category:
            stmt = stmt.where(RequestHelp.category == category)
        result = await session.exec(stmt)
        return result.all()

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
        return await self.get_request(request.id, session)

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
        return await self.get_request(request.id, session)

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
        return await self.get_request(request.id, session)

    async def get_my_requests(self, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(RequestHelp)
            .where(RequestHelp.requester_id == user_id)
            .options(selectinload(RequestHelp.applications))
        )
        return result.all()

    async def get_my_applications(self, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(HelpApplication).where(HelpApplication.applicant_id == user_id)
        )
        return result.all()