from typing import Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    name: Optional[str] = None
    company_name: Optional[str] = None # Added based on frontend

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserInDBBase(UserBase):
    id: Optional[int] = None
    name: Optional[str] = None
    company_name: Optional[str] = None
    role: str

    class Config:
        from_attributes = True # updated for pydantic v2 compatibility if needed, else orm_mode = True

class User(UserInDBBase):
    pass

class UserInDB(UserInDBBase):
    hashed_password: str
