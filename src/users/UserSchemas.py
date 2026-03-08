from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str  = Field(min_length=6)

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    profile_image_path: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str  = Field(min_length=6)

class UserModel(BaseModel):
    id: int
    username: str
    email: str
    profile_image_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True