from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class FileBase(BaseModel):
    file_name: str
    file_type: str

class FileCreate(FileBase):
    storage_path: str
    negotiation_id: Optional[int] = None
    user_id: Optional[int] = None

class File(FileBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    # We don't expose storage_path to the frontend for security

    class Config:
        from_attributes = True
