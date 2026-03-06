from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    negotiation_id = Column(Integer, ForeignKey("negotiations.id"), nullable=True) # Nullable because files might be uploaded before negotiation starts
    file_name = Column(String)
    file_type = Column(String)
    storage_path = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="files")
    negotiation = relationship("Negotiation", backref="files")
