from pydantic import BaseModel

class ConversationResponse(BaseModel):
    user1_id: int
    user2_id: int