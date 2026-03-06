from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class MessageBase(BaseModel):
    sender: str
    content: str

class MessageCreate(MessageBase):
    negotiation_id: int

class Message(MessageBase):
    id: int
    negotiation_id: int
    timestamp: datetime

    class Config:
        from_attributes = True
