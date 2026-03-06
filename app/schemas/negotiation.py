from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class NegotiationBase(BaseModel):
    supplier_name: str
    deal_value: float
    tone: str
    goal: str
    autonomy_mode: str

class NegotiationCreate(NegotiationBase):
    pass

class NegotiationUpdate(NegotiationBase):
    status: Optional[str] = None

class Negotiation(NegotiationBase):
    id: int
    user_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
