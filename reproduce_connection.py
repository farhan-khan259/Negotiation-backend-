
import os
import asyncio
from dotenv import load_dotenv

# Try imports
try:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    print("WARNING: sqlalchemy not found")

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    print("WARNING: psycopg2 not found")

try:
    import sys
    sys.path.append(os.getcwd())
    from app.core.config import settings
    HAS_SETTINGS = True
except ImportError as e:
    HAS_SETTINGS = False
    print(f"WARNING: Could not import app.core.config.settings: {e}")

# Load env vars
load_dotenv()

async def test_async_engine(url, name):
    if not HAS_SQLALCHEMY:
        print(f"SKIPPING {name} (Async): sqlalchemy missing")
        return

    print(f"\n--- Testing {name} (Async) ---")
    print(f"URL: {url}")
    
    try:
        # Add SSL for Supabase if needed (settings usually handles this but for raw URL testing)
        if "supabase.co" in url and "ssl=" not in url:
             if "?" in url:
                url += "&ssl=require"
             else:
                url += "?ssl=require"
        
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"SUCCESS: Connected to {name} and executed SELECT 1")
    except Exception as e:
        print(f"FAILURE: Could not connect to {name}. Error: {e}")

def test_sync_connection(url, name):
    if not HAS_PSYCOPG2:
        print(f"SKIPPING {name} (Sync psycopg2): psycopg2 missing")
        return

    print(f"\n--- Testing {name} (Sync psycopg2) ---")
    print(f"URL: {url}")
    try:
        conn = psycopg2.connect(url)
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            print(f"SUCCESS: Connected to {name} and executed SELECT 1")
        conn.close()
    except Exception as e:
        print(f"FAILURE: Could not connect to {name}. Error: {e}")

async def main():
    if HAS_SETTINGS:
        # Test 1: Async URL from settings (used by FastAPI)
        print(f"DEBUG: settings.DATABASE_URL: {settings.DATABASE_URL}")
        await test_async_engine(settings.DATABASE_URL, "Settings Async URL")

        # Test 2: Sync URL from settings (used by RAG)
        try:
            sync_url = settings.get_sync_db_url()
            print(f"DEBUG: settings.get_sync_db_url(): {sync_url}")
            test_sync_connection(sync_url, "Settings Sync URL")
        except Exception as e:
             print(f"DEBUG: Failed to get sync url: {e}")
    else:
        print("Skipping settings tests due to import error")

if __name__ == "__main__":
    asyncio.run(main())
