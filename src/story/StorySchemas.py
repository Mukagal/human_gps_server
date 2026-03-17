from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class StoryCreate(BaseModel):
    image_path: str
    caption: Optional[str] = None

class StoryResponse(BaseModel):
    id: int
    author_id: int
    image_path: str
    caption: Optional[str] = None
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True