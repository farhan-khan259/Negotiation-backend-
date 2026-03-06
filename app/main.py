from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine, enable_pgvector_extension, create_vector_indexes, ensure_user_scope_columns
from app.db.base import Base

# Import all models to register them with SQLAlchemy before creating tables
from app.models.user import User  # noqa: F401
from app.models.file import File  # noqa: F401
from app.models.negotiation import Negotiation  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.embedding import Embedding  # noqa: F401

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Autonomous AI Negotiation Platform",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def init_tables():
    try:
        # Enable pgvector extension first (required before creating tables with vector columns)
        await enable_pgvector_extension()
        
        # Then create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✓ Database tables initialized successfully")
        
        # Ensure user scoping columns exist for data isolation
        await ensure_user_scope_columns()
        
        # Create indexes for vector similarity search performance
        await create_vector_indexes()
        
    except Exception as e:
        print(f"Warning: Could not connect to database: {e}")
        print("The API will start but database operations will fail.")
        print("Please ensure PostgreSQL is running and DATABASE_URL is configured correctly.")

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Negotiation Platform API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

