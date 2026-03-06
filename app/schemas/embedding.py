from typing import Optional, List
from pydantic import BaseModel


class EmbeddingBase(BaseModel):
    user_id: Optional[int] = None
    file_id: int
    chunk_index: int
    content: str
    metadata_json: Optional[str] = None


class EmbeddingCreate(EmbeddingBase):
    vector: List[float]


class Embedding(EmbeddingBase):
    id: int
    
    class Config:
        from_attributes = True
