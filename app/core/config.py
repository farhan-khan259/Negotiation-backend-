from typing import List, Union
from pydantic import validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")
    PROJECT_NAME: str = "AI Negotiation Platform"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS - use Field to handle string from .env
  BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000,https://neggle.com,https://www.neggle.com,https://be.neggle.com"

    # Database
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ai_negotiation"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = ""

    # Supabase docs-style envs (psycopg2 examples use lowercase names)
    DB_HOST: str = Field(default="", env="host")
    DB_USER: str = Field(default="", env="user")
    DB_PASSWORD: str = Field(default="", env="password")
    DB_NAME: str = Field(default="", env="dbname")
    DB_PORT: int = Field(default=5432, env="port")

    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: str, values: dict) -> str:
        if isinstance(v, str) and v:
            # Ensure asyncpg driver for async engine
            if v.startswith("postgresql://"):
                url = v.replace("postgresql://", "postgresql+asyncpg://")
                # asyncpg does not support sslmode, it uses ssl=...
                if "sslmode=" in url:
                    url = url.replace("sslmode=disable", "")
                    url = url.replace("sslmode=require", "")
                    url = url.replace("sslmode=verify-full", "")
                    url = url.replace("sslmode=verify-ca", "")
                    # Clean up trailing ? or &
                    if url.endswith("?"): url = url[:-1]
                    if url.endswith("&"): url = url[:-1]
                return url
            return v
        
        # Assemble from components if URL not provided
        server = values.get('POSTGRES_SERVER') or values.get('DB_HOST')
        user = values.get('POSTGRES_USER') or values.get('DB_USER')
        password = values.get('POSTGRES_PASSWORD') or values.get('DB_PASSWORD')
        db = values.get('POSTGRES_DB') or values.get('DB_NAME')
        port = values.get('POSTGRES_PORT') or values.get('DB_PORT', 5432)
        
        if not (server and user and password and db):
            return ""
        
        # Default to asyncpg for main app with port
        return f"postgresql+asyncpg://{user}:{password}@{server}:{port}/{db}"

    def get_sync_db_url(self) -> str:
        """Get synchronous database URL for tools like LangChain/Alembic"""
        if self.DATABASE_URL and "+asyncpg" in self.DATABASE_URL:
             return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")
        
        if self.DATABASE_URL:
             return self.DATABASE_URL
             
        server = self.POSTGRES_SERVER or self.DB_HOST
        user = self.POSTGRES_USER or self.DB_USER
        password = self.POSTGRES_PASSWORD or self.DB_PASSWORD
        db = self.POSTGRES_DB or self.DB_NAME

        if server and user and password and db:
            return f"postgresql+psycopg2://{user}:{password}@{server}/{db}"
            
        return ""

    # AI
    OPENAI_API_KEY: str = "sk-placeholder-key"
    
    # Pinecone
    PINECONE_API_KEY: str = Field(default="", env="PINECONE_API_KEY")
    PINECONE_INDEX_NAME: str = "negotiation-index"

    # Supabase
    SUPABASE_URL: str = Field(default="", env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(default="", env="SUPABASE_KEY")
    SUPABASE_BUCKET_NAME: str = "negotiation-files"

    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]
        return self.BACKEND_CORS_ORIGINS


settings = Settings()
