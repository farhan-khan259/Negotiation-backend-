from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    negotiation_id = Column(Integer, ForeignKey("negotiations.id"))
    sender = Column(String) # buyer | ai | supplier
    content = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    negotiation = relationship("Negotiation", backref="messages")
