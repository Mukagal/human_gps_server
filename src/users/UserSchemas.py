from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserModel(BaseModel):
    id: int
    username: str
    email: str
    profile_image_path: Optional[str] = None
    created_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    role: str = "user"
    is_verified: bool = False
    is_banned: bool = False
    ban_reason: Optional[str] = None
    rating: float = 0.0

    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    id: int
    username: str
    profile_image_path: Optional[str] = None

    class Config:
        from_attributes = True


class UserSafe(BaseModel):
    id: int
    username: str
    email: str
    profile_image_path: Optional[str] = None
    created_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    role: str = "user"
    is_verified: bool = False
    is_banned: bool = False
    ban_reason: Optional[str] = None
    rating: float = None

    class Config:
        from_attributes = True

class UserLocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(min_length=6)