from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from app.models.embedding import Embedding
from app.schemas.embedding import EmbeddingCreate


async def create(db: AsyncSession, obj_in: EmbeddingCreate) -> Embedding:
    """Create an embedding record."""
    db_obj = Embedding(**obj_in.dict())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get(db: AsyncSession, id: int) -> Optional[Embedding]:
    """Get an embedding by ID."""
    stmt = select(Embedding).where(Embedding.id == id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_file_id(db: AsyncSession, file_id: int) -> List[Embedding]:
    """Get all embeddings for a file."""
    stmt = select(Embedding).where(Embedding.file_id == file_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def delete(db: AsyncSession, id: int) -> Optional[Embedding]:
    """Delete an embedding by ID."""
    obj = await get(db, id)
    if obj:
        await db.delete(obj)
        await db.commit()
    return obj


async def delete_by_file_id(db: AsyncSession, file_id: int) -> int:
    """Delete all embeddings for a file. Returns count of deleted records."""
    stmt = select(Embedding).where(Embedding.file_id == file_id)
    result = await db.execute(stmt)
    embeddings = result.scalars().all()
    
    for embedding in embeddings:
        await db.delete(embedding)
    
    await db.commit()
    return len(embeddings)
