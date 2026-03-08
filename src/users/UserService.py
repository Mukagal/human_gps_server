from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import delete, select

from ..users.utils import generate_password_hash
from ..db.models import User, GroupMember
from .UserSchemas import UserCreate, UserUpdate
from datetime import datetime
from sqlalchemy.exc import IntegrityError  
from fastapi import HTTPException



class UserService:

    async def get_all_users(self, session: AsyncSession):
        result = await session.exec(select(User))
        return result.all()

    async def get_user(self, user_id: int, session: AsyncSession):
        result = await session.exec(
            select(User).where(User.id == user_id)
        )
        return result.first()
    
    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)

        result = await session.exec(statement)

        user = result.first()

        return user
    
    async def user_exists(self, email, session: AsyncSession):
        user = await self.get_user_by_email(email, session)

        return True if user is not None else False

    async def create_user(self, user_data: UserCreate, session: AsyncSession):
        user_data_dict = user_data.model_dump()

        user_data_dict["password"] = generate_password_hash(user_data_dict["password"])
        new_user = User(**user_data_dict)

        session.add(new_user)

        await session.commit()

        return new_user
    
    async def update_user(self, user_id: int, update_data: UserUpdate, session: AsyncSession):

        user = await self.get_user(user_id, session)

        if not user:
            return None

        for k, v in update_data.model_dump(exclude_unset=True).items():
            setattr(user, k, v)

        await session.commit()
        await session.refresh(user)
        return user

    async def delete_user(self, user_id: int, session: AsyncSession):

        await session.exec(
            delete(GroupMember).where(GroupMember.user_id == user_id)
        )

        result = await session.exec(
            select(User).where(User.id == user_id)
        )

        user = result.first()

        if not user:
            return False

        await session.delete(user)
        await session.commit()

        return True