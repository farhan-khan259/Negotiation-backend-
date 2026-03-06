from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import ssl

from app.core.config import settings

engine_kwargs = {
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20,
    "future": True,
    "echo": True,
}

# Configure SSL for Supabase
if "supabase" in settings.DATABASE_URL:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    engine_kwargs["connect_args"] = {"ssl": ssl_context}

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def enable_pgvector_extension():
    """Enable pgvector extension in PostgreSQL (required for vector similarity search)."""
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import text
            
            # Check if extension already exists
            result = await session.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            )
            exists = result.scalar()
            
            if exists:
                print("✓ pgvector extension already enabled")
            else:
                # Create the extension
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await session.commit()
                print("✓ pgvector extension enabled successfully")
                
        except Exception as e:
            print(f"⚠ Warning: Could not enable pgvector extension: {e}")
            print("  If using Supabase, enable it manually in SQL Editor: CREATE EXTENSION vector;")
            raise


async def create_vector_indexes():
    """Create indexes for vector similarity search performance."""
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import text
            
            # Create ivfflat index for cosine similarity (pgvector)
            # Using ivfflat for better performance on similarity searches
            await session.execute(text(
                "CREATE INDEX IF NOT EXISTS embeddings_vector_idx "
                "ON embeddings USING ivfflat (vector vector_cosine_ops) "
                "WITH (lists = 100)"
            ))
            await session.commit()
            print("✓ Vector similarity search indexes created")
            
        except Exception as e:
            # Index creation might fail if table doesn't exist yet or index already exists
            print(f"ℹ Note: Vector index creation skipped: {e}")
            # Don't raise - this is not critical for startup


async def ensure_user_scope_columns():
    """Ensure user_id columns exist for per-user access control."""
    async with AsyncSessionLocal() as session:
        try:
            from sqlalchemy import text

            await session.execute(text(
                "DO $$\n"
                "BEGIN\n"
                "  IF NOT EXISTS (\n"
                "    SELECT 1 FROM information_schema.columns\n"
                "    WHERE table_name='files' AND column_name='user_id'\n"
                "  ) THEN\n"
                "    ALTER TABLE files ADD COLUMN user_id INTEGER;\n"
                "  END IF;\n"
                "END $$;"
            ))

            await session.execute(text(
                "DO $$\n"
                "BEGIN\n"
                "  IF NOT EXISTS (\n"
                "    SELECT 1 FROM information_schema.columns\n"
                "    WHERE table_name='embeddings' AND column_name='user_id'\n"
                "  ) THEN\n"
                "    ALTER TABLE embeddings ADD COLUMN user_id INTEGER;\n"
                "  END IF;\n"
                "END $$;"
            ))

            await session.execute(text(
                "CREATE INDEX IF NOT EXISTS files_user_id_idx ON files (user_id)"
            ))
            await session.execute(text(
                "CREATE INDEX IF NOT EXISTS embeddings_user_id_idx ON embeddings (user_id)"
            ))

            await session.commit()
            print("✓ User scope columns ensured")

        except Exception as e:
            print(f"⚠ Warning: Could not ensure user scope columns: {e}")
            # Don't raise - app can still run, but isolation may be incomplete