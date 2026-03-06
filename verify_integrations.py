
import os
import asyncio
from dotenv import load_dotenv
from app.core.config import settings
from app.core import rag

# Load env vars
load_dotenv()

async def verify_pinecone():
    print("--- Verifying OpenAI Embeddings ---")

    if not settings.OPENAI_API_KEY or "placeholder" in settings.OPENAI_API_KEY:
        print("SKIPPING: OPENAI_API_KEY is missing or is placeholder. Please set it in .env")
        return

    try:
        embeddings = rag._get_embeddings()
        vector = embeddings.embed_query("connectivity check")
        if vector:
            print("SUCCESS: OpenAI embeddings initialized and returned a vector")
        else:
            print("FAILURE: OpenAI embeddings returned an empty vector")
    except Exception as e:
        print(f"FAILURE: Exception during OpenAI embeddings initialization: {e}")

async def verify_supabase():
    print("\n--- Verifying Supabase Data Connection ---")
    # Using existing check logic
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        url = settings.DATABASE_URL
        print(f"Database URL: {url}")
        
        engine = create_async_engine(url)
        # Verify connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            print("SUCCESS: Connected to Supabase (Postgres)!")
    except Exception as e:
        print(f"FAILURE: Could not connect to Supabase: {e}")

if __name__ == "__main__":
    asyncio.run(verify_supabase())
    asyncio.run(verify_pinecone())
