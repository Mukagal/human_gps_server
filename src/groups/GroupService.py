from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from ..db.models import GroupChat, GroupMember, GroupMessage
from .GroupSchemas import GroupCreate, GroupMessageSend


class GroupService:

    async def create_group(self, data: GroupCreate, session: AsyncSession):
        group = GroupChat(name=data.name, created_by=data.created_by)
        session.add(group)
        await session.flush()   

        for user_id in set(data.member_ids):
            session.add(GroupMember(group_id=group.id, user_id=user_id))

        await session.commit()
        await session.refresh(group)
        return group

    async def get_group(self, group_id: int, session: AsyncSession):
        result = await session.exec(
            select(GroupChat).where(GroupChat.id == group_id)
        )
        return result.first()

    async def get_user_groups(self, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(GroupChat)
            .join(GroupMember, GroupMember.group_id == GroupChat.id)
            .where(GroupMember.user_id == user_id)
        )
        return result.all()

    async def send_message(self, group_id: int, data: GroupMessageSend, session: AsyncSession):
        member = await session.exec(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == data.sender_id
            )
        )
        if not member.first():
            raise HTTPException(status_code=403, detail="User not in this group")

        msg = GroupMessage(
            group_id=group_id,
            sender_id=data.sender_id,
            content=data.content
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)
        return msg

    async def get_messages(self, group_id: int, session: AsyncSession):
        result = await session.exec(
            select(GroupMessage)
            .where(GroupMessage.group_id == group_id)
            .order_by(GroupMessage.sent_at)
        )
        return result.all()

    async def add_member(self, group_id: int, user_id: int, session: AsyncSession):
        session.add(GroupMember(group_id=group_id, user_id=user_id))
        await session.commit()

    async def remove_member(self, group_id: int, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id
            )
        )
        member = result.first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        await session.delete(member)
        await session.commit()