from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MessageBase(BaseModel):
    content: str
    sender_id: int
    receiver_id: int
    
class MessageSend(BaseModel):
    content: str

class MessageResponse(MessageBase):
    id: int
    sent_at: datetime
    received_at: Optional[datetime] = None
    conversation_id: int

    class Config:
        from_attributes = True

class MessageUpdate(BaseModel):
    content: str

class MessageDelete(BaseModel):
    id: int
    sender_id: int