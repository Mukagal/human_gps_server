from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from ..db.main import get_session
from .GroupService import GroupService
from .GroupSchemas import GroupCreate, GroupMessageSend

group_router = APIRouter()
group_service = GroupService()


@group_router.post("/groups")
async def create_group(data: GroupCreate, session: AsyncSession = Depends(get_session)):
    return await group_service.create_group(data, session)


@group_router.get("/groups/{group_id}")
async def get_group(group_id: int, session: AsyncSession = Depends(get_session)):
    group = await group_service.get_group(group_id, session)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@group_router.get("/users/{user_id}/groups")
async def get_user_groups(user_id: int, session: AsyncSession = Depends(get_session)):
    return await group_service.get_user_groups(user_id, session)


@group_router.post("/groups/{group_id}/messages")
async def send_message(
    group_id: int,
    data: GroupMessageSend,
    session: AsyncSession = Depends(get_session)
):
    return await group_service.send_message(group_id, data, session)


@group_router.get("/groups/{group_id}/messages")
async def get_messages(group_id: int, session: AsyncSession = Depends(get_session)):
    return await group_service.get_messages(group_id, session)


@group_router.post("/groups/{group_id}/members/{user_id}")
async def add_member(
    group_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    await group_service.add_member(group_id, user_id, session)
    return {"message": "Member added"}


@group_router.delete("/groups/{group_id}/members/{user_id}")
async def remove_member(
    group_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    await group_service.remove_member(group_id, user_id, session)
    return {"message": "Member removed"}