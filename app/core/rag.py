import json
import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.core.config import settings
from app.models.embedding import Embedding
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Lazy-initialized embeddings
_embeddings: Optional[OpenAIEmbeddings] = None


def _get_embeddings():
    """Lazy initialize embeddings."""
    global _embeddings
    if _embeddings is None:
        if not settings.OPENAI_API_KEY or "placeholder" in settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY is not set or is a placeholder")
        _embeddings = OpenAIEmbeddings(
            api_key=settings.OPENAI_API_KEY,
            model="text-embedding-3-large",
            dimensions=1024
        )
    return _embeddings


async def ingest_text(text: str, metadata: dict):
    """
    Chunks text and stores embeddings in PostgreSQL using pgvector.
    
    Args:
        text: The text content to ingest
        metadata: Dict containing file_id, file_name, file_type, user_id, etc.
    """
    if not text:
        logger.warning("Empty text provided for ingestion")
        return

    try:
        file_id = metadata.get("file_id")
        user_id = metadata.get("user_id")
        if not file_id:
            logger.error("file_id is required in metadata for ingestion")
            raise ValueError("file_id is required in metadata")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )
        
        docs = [Document(page_content=x, metadata=metadata) for x in text_splitter.split_text(text)]
        
        # Get embeddings for all chunks
        embeddings = _get_embeddings().embed_documents([d.page_content for d in docs])
        
        # Store embeddings in PostgreSQL
        async with AsyncSessionLocal() as session:
            for i, (doc, vector) in enumerate(zip(docs, embeddings)):
                embedding_obj = Embedding(
                    user_id=int(user_id) if user_id is not None else None,
                    file_id=int(file_id),
                    chunk_index=i,
                    content=doc.page_content,
                    vector=vector,
                    metadata_json=json.dumps(doc.metadata) if doc.metadata else None
                )
                session.add(embedding_obj)
            
            await session.commit()
        
        logger.info(f"Successfully ingested {len(docs)} chunks into pgvector with file_id={file_id}")
        print(f"DEBUG: Ingested {len(docs)} chunks into pgvector for file_id={file_id}.")
        
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        print(f"ERROR: pgvector ingestion failed: {e}")
        raise


async def retrieve_similar(query: str, top_k: int = 4, user_id: Optional[int] = None) -> List[Document]:
    """
    Retrieve similar documents using pgvector similarity search.
    
    Args:
        query: The query text
        top_k: Number of top results to return
    
    Returns:
        List of Document objects with matching content
    """
    try:
        embeddings = _get_embeddings()
        query_vector = embeddings.embed_query(query)
        
        async with AsyncSessionLocal() as session:
            # Use pgvector <-> operator for cosine similarity (L2 distance)
            stmt = select(Embedding)
            if user_id is not None:
                stmt = stmt.where(Embedding.user_id == user_id)

            stmt = stmt.order_by(
                Embedding.vector.cosine_distance(query_vector)
            ).limit(top_k)
            
            result = await session.execute(stmt)
            embedding_records = result.scalars().all()
            
            docs = []
            for record in embedding_records:
                metadata = {}
                if record.metadata_json:
                    try:
                        metadata = json.loads(record.metadata_json)
                    except json.JSONDecodeError:
                        pass
                
                doc = Document(
                    page_content=record.content,
                    metadata={
                        **metadata,
                        "embedding_id": record.id,
                        "file_id": record.file_id,
                    }
                )
                docs.append(doc)
            
            return docs
            
    except Exception as e:
        logger.warning(f"Retrieval error: {e}")
        print(f"ERROR: pgvector retrieval failed: {e}")
        return []


class PGVectorRetriever:
    """Custom retriever backed by PostgreSQL pgvector."""
    
    def __init__(self, top_k: int = 4, user_id: Optional[int] = None):
        self.top_k = top_k
        self.user_id = user_id

    async def ainvoke(self, query: str) -> List[Document]:
        """Async invoke - retrieve similar documents."""
        return await retrieve_similar(query, top_k=self.top_k, user_id=self.user_id)

    def invoke(self, query: str) -> List[Document]:
        """Sync invoke - not recommended for async application."""
        logger.warning("Using sync invoke on async retriever. Consider using ainvoke instead.")
        raise NotImplementedError("Use ainvoke for async retriever")


def get_retriever(top_k: int = 5, user_id: Optional[int] = None) -> PGVectorRetriever:
    """Returns a pgvector-backed retriever scoped to a user."""
    return PGVectorRetriever(top_k=top_k, user_id=user_id)