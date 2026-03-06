from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.negotiation import Negotiation
from app.models.message import Message
from app.schemas.negotiation import NegotiationCreate, NegotiationUpdate
from app.schemas.message import MessageCreate

async def create_negotiation(db: AsyncSession, obj_in: NegotiationCreate, user_id: int) -> Negotiation:
    db_obj = Negotiation(
        user_id=user_id,
        supplier_name=obj_in.supplier_name,
        deal_value=obj_in.deal_value,
        tone=obj_in.tone,
        goal=obj_in.goal,
        autonomy_mode=obj_in.autonomy_mode,
        status="active"
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_negotiation(db: AsyncSession, negotiation_id: int, user_id: Optional[int] = None) -> Optional[Negotiation]:
    stmt = select(Negotiation).filter(Negotiation.id == negotiation_id)
    if user_id is not None:
        stmt = stmt.filter(Negotiation.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().first()

async def create_message(db: AsyncSession, obj_in: MessageCreate) -> Message:
    db_obj = Message(
        negotiation_id=obj_in.negotiation_id,
        sender=obj_in.sender,
        content=obj_in.content
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_messages(db: AsyncSession, negotiation_id: int) -> List[Message]:
    result = await db.execute(select(Message).filter(Message.negotiation_id == negotiation_id).order_by(Message.timestamp))
    return result.scalars().all()
