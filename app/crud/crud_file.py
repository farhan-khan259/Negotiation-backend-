from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.file import File
from app.schemas.file import FileCreate

async def create(db: AsyncSession, obj_in: FileCreate) -> File:
    db_obj = File(
        user_id=obj_in.user_id,
        file_name=obj_in.file_name,
        file_type=obj_in.file_type,
        storage_path=obj_in.storage_path,
        negotiation_id=obj_in.negotiation_id
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_multi_by_negotiation(db: AsyncSession, negotiation_id: int) -> List[File]:
    result = await db.execute(select(File).filter(File.negotiation_id == negotiation_id))
    return result.scalars().all()

async def get_all(db: AsyncSession) -> List[File]:
    result = await db.execute(select(File))
    return result.scalars().all()

async def get_all_for_user(db: AsyncSession, user_id: int) -> List[File]:
    result = await db.execute(select(File).filter(File.user_id == user_id))
    return result.scalars().all()
