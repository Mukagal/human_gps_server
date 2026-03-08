from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db.models import User
from ..users.dependencies import get_current_user
from ..db.main import get_session
from .ConversationService import ConversationService
from ..groups.GroupService import GroupService
from ..messages.MessageService import MessageService  

conversation_router = APIRouter()
conversation_service = ConversationService()
message_service = MessageService() 
group_service = GroupService()

@conversation_router.post("/conversations")
async def create_conversation(
    user_b: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)  
):
    return await conversation_service.create_conversation(current_user.id, user_b, session)

@conversation_router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return await conversation_service.get_conversation(
        conversation_id, session
    )

@conversation_router.get("/users/{user_id}/conversations")
async def get_user_conversations(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    return await conversation_service.get_user_conversations(current_user.id, session)

@conversation_router.get("/conversations/{conversation_id}/full")
async def get_conversation_with_messages(
    conversation_id: int,
    session: AsyncSession = Depends(get_session)
):
    conversation = await conversation_service.get_conversation(conversation_id, session)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = await message_service.get_conversation_messages(conversation_id, session)
    return {"conversation": conversation, "messages": messages}

@conversation_router.get("/users/{user_id}/inbox")
async def get_inbox(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    conversations = await conversation_service.get_user_conversations(current_user.id, session)
    groups = await group_service.get_user_groups(current_user.id, session)
    return {
        "conversations": conversations,
        "group_chats": groups
    }