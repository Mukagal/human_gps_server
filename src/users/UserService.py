from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import delete, select

from ..users.utils import generate_password_hash
from ..db.models import User, GroupMember
from .UserSchemas import UserCreate, UserUpdate
from datetime import datetime
from sqlalchemy.exc import IntegrityError  
from fastapi import HTTPException

import cloudinary
import cloudinary.uploader
from ..config import Config
from fastapi import UploadFile
import math

cloudinary.config(
    cloud_name=Config.CLOUDINARY_CLOUD_NAME,
    api_key=Config.CLOUDINARY_API_KEY,
    api_secret=Config.CLOUDINARY_API_SECRET
)



class UserService:

    async def get_all_users(self, session: AsyncSession, username: Optional[str] = None):
        statement = select(User)
        if username:
            statement = statement.where(User.username.ilike(f"%{username}%"))
        result = await session.exec(statement)
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
            if k == "password":  
                from src.users.utils import generate_password_hash
                v = generate_password_hash(v)
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
    
    async def upload_profile_image(self, user_id: int, file: UploadFile, session: AsyncSession):
        user = await self.get_user(user_id, session)
        if not user:
            return None

        result = cloudinary.uploader.upload(
            file.file,
            folder="profile_images",
            public_id=f"user_{user_id}",
            overwrite=True,
            transformation=[
                {"width": 300, "height": 300, "crop": "fill", "gravity": "face"}
            ]
        )

        user.profile_image_path = result["secure_url"]
        await session.commit()
        await session.refresh(user)
        return user
    
    async def update_location(self, user_id: int, latitude: float, logtitude: float, session:AsyncSession):
        user = await self.get_user(user_id, session)
        if not user:
            return None
        user.latitude = latitude
        user.longitude = logtitude
        await session.commit()
        await session.refresh(user)
        return user
    async def get_nearby_users(self, latitude: float, longitude: float, radius_km: float, session: AsyncSession):

        result = await session.exec(
            select(User).where(User.latitude.isnot(None), User.longitude.isnot(None))
        )
        all_users = result.all()

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371 
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            return R * 2 * math.asin(math.sqrt(a))

        nearby = []
        for user in all_users:
            dist = haversine(latitude, longitude, user.latitude, user.longitude)
            if dist <= radius_km:
                nearby.append({"user": user, "distance_km": round(dist, 2)})

        nearby.sort(key=lambda x: x["distance_km"])
        return nearby