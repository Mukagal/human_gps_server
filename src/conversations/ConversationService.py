from sqlmodel import select
from fastapi import HTTPException
from ..db.models import Conversation
from sqlmodel.ext.asyncio.session import AsyncSession
from ..errors import SelfConversationError


class ConversationService:

    async def create_conversation(self, user_a: int, user_b: int, session: AsyncSession):

        if user_a == user_b:
            raise SelfConversationError

        user1_id = min(user_a, user_b)
        user2_id = max(user_a, user_b)

        statement = select(Conversation).where(
            Conversation.user1_id == user1_id,
            Conversation.user2_id == user2_id
        )

        result = await session.exec(statement)
        existing = result.first()

        if existing:
            return existing

        new_conv = Conversation(
            user1_id=user1_id,
            user2_id=user2_id
        )

        session.add(new_conv)
        await session.commit()
        await session.refresh(new_conv)

        return new_conv

    async def get_conversation(self, conversation_id: int, session: AsyncSession):
        result = await session.exec(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.first()
    async def get_user_conversations(self, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(Conversation).where(
                (Conversation.user1_id == user_id) | (Conversation.user2_id == user_id)
            )
        )
        return result.all()