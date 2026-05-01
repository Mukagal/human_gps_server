from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional

class MessageBase(BaseModel):
    content: str
    sender_id: int
    receiver_id: int

    @field_validator('content')
    @classmethod
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()
    
class MessageSend(BaseModel):
    content: str

    @field_validator('content')
    @classmethod
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()
    
class MessageResponse(MessageBase):
    id: int
    sent_at: datetime
    received_at: Optional[datetime] = None
    conversation_id: int

    class Config:
        from_attributes = True

class MessageUpdate(BaseModel):
    content: str
    
    @field_validator('content')
    @classmethod
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()

class MessageDelete(BaseModel):
    id: int
    sender_id: int