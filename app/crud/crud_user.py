from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate

async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()

async def create(db: AsyncSession, obj_in: UserCreate) -> User:
    db_obj = User(
        email=obj_in.email,
        hashed_password=get_password_hash(obj_in.password),
        name=obj_in.name,
        company_name=obj_in.company_name,
        role="buyer" # Default role
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def authenticate(db: AsyncSession, email: str, password: str) -> Optional[User]:
    print(f"DEBUG: Authenticating user: {email}")
    user = await get_by_email(db, email)
    print(f"DEBUG: User found: {user is not None}")
    if not user:
        print(f"DEBUG: No user found with email: {email}")
        return None
    print(f"DEBUG: Checking password...")
    if not verify_password(password, user.hashed_password):
        print(f"DEBUG: Password verification failed")
        return None
    print(f"DEBUG: Authentication successful for user: {email}")
    return user
