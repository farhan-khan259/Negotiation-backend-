from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base


class Embedding(Base):
    """Vector embeddings stored in PostgreSQL with pgvector extension."""
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    chunk_index = Column(Integer)  # Index of chunk within the document
    content = Column(Text, nullable=False)  # Original chunk text
    vector = Column(Vector(1024), nullable=False)  # 1024-dim embedding from text-embedding-3-large
    metadata_json = Column(String, nullable=True)  # JSON string for additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="embeddings")
    file = relationship("File", backref="embeddings")
