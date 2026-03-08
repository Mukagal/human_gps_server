from fastapi import HTTPException
from sqlmodel import select, desc

from ..messages.MessageSchemas import MessageUpdate
from ..db.models import Message, Conversation
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime


class MessageService:

    async def send_message(self, conversation_id: int, message_data, sender_id: int, session):
        conversation = await session.get(Conversation, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if sender_id not in {conversation.user1_id, conversation.user2_id}:
            raise HTTPException(status_code=400, detail="Sender not in conversation")

        receiver_id = (
            conversation.user2_id if sender_id == conversation.user1_id
            else conversation.user1_id
        )

        new_message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=message_data.content
        )

        session.add(new_message)
        await session.commit()
        await session.refresh(new_message)
        return new_message

    async def get_conversation_messages(self, conversation_id: int, session: AsyncSession):

        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.sent_at))
        )

        result = await session.exec(statement)
        return result.all()
    
    async def update_message(self, message_id: int, sender_id: int, update_data: MessageUpdate, session: AsyncSession):
        result = await session.exec(select(Message).where(Message.id == message_id))
        message = result.first()

        if not message:
            return None
        if message.sender_id != sender_id:
            raise HTTPException(status_code=403, detail="Not your message")

        message.content = update_data.content
        await session.commit()
        await session.refresh(message)
        return message

    async def delete_message(self, message_id: int, sender_id: int, session: AsyncSession):
        result = await session.exec(select(Message).where(Message.id == message_id))
        message = result.first()

        if not message:
            return None
        if message.sender_id != sender_id:
            raise HTTPException(status_code=403, detail="Not your message")

        await session.delete(message)
        await session.commit()
        return {}