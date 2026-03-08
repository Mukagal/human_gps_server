from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class GroupCreate(BaseModel):
    name: str
    created_by: int
    member_ids: List[int]      

class GroupMessageSend(BaseModel):
    sender_id: int
    content: str

class GroupMessageResponse(BaseModel):
    id: int
    group_id: int
    sender_id: int            
    content: str
    sent_at: datetime

    class Config:
        from_attributes = True

class GroupChatResponse(BaseModel):
    id: int
    name: str
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True