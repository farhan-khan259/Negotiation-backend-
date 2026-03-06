from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Negotiation(Base):
    __tablename__ = "negotiations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    supplier_name = Column(String, index=True)
    deal_value = Column(Float)
    tone = Column(String)
    goal = Column(String)
    autonomy_mode = Column(String) # 'autonomous' or 'human-in-loop'
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="negotiations")
