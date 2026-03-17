from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SortBy(str, Enum):
    latest   = "latest"
    likes    = "likes"
    comments = "comments"


class PostCreate(BaseModel):
    content: str


class PostUpdate(BaseModel):
    content: Optional[str] = None
    image_path: Optional[str] = None


class PostResponse(BaseModel):
    id: int
    author_id: int
    content: str
    image_path: Optional[str] = None
    created_at: datetime
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0

    class Config:
        from_attributes = True


class LikeResponse(BaseModel):
    post_id: int
    user_id: int
    liked_at: datetime

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: int
    post_id: int
    author_id: int
    content: str
    created_at: datetime
    author_username: Optional[str] = None

    class Config:
        from_attributes = True


class ShareRequest(BaseModel):
    conversation_id: Optional[int] = None
    group_id: Optional[int] = None


class ShareResponse(BaseModel):
    id: int
    post_id: int
    shared_by: int
    conversation_id: Optional[int] = None
    group_id: Optional[int] = None
    share_link: str
    shared_at: datetime

    class Config:
        from_attributes = True