from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from ..middlware.rate_limit import limiter, WRITE_LIMIT, GENERAL_LIMIT_MIN
from ..users.dependencies import get_current_user

from ..db.main import get_session
from .MessageService import MessageService
from .MessageSchemas import MessageSend
from ..db.models import Message, User
from .MessageSchemas import MessageSend, MessageUpdate

message_router = APIRouter()
message_service = MessageService()

@message_router.post("/conversations/{conversation_id}/messages")
@limiter.limit(WRITE_LIMIT)
async def send_message(
    request:Request,
    conversation_id: int,
    message_data: MessageSend,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await message_service.send_message(
        conversation_id,
        message_data,
        current_user.id,
        session
    )

@message_router.get("/conversations/{conversation_id}/messages", response_model=List[Message])
async def get_messages(
    conversation_id: int,
    limit: int = 20,
    session: AsyncSession = Depends(get_session)
):
    messages = await message_service.get_conversation_messages(
        conversation_id, session
    )
    return messages[:limit]

@message_router.patch("/messages/{message_id}")
@limiter.limit(WRITE_LIMIT)
async def update_message(
    request:Request,
    message_id: int,
    update_data: MessageUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    message = await message_service.update_message(message_id, current_user.id, update_data, session)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message

@message_router.delete("/messages/{message_id}")
@limiter.limit(WRITE_LIMIT)
async def delete_message(
    request:Request,
    message_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    deleted = await message_service.delete_message(message_id, current_user.id, session)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Deleted"}