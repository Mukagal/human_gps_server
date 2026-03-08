from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PostBase(BaseModel):
    author_id: int
    content: str

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    content: Optional[str] = None

class PostResponse(PostBase):
    id: int
    author_id: int
    image_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True