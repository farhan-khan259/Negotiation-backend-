from typing import Any, List
import os
from fastapi import APIRouter, Depends, UploadFile, File as FastAPIFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.files import save_upload_file, extract_text_from_file, upload_to_supabase
from app.core.rag import ingest_text
from app.crud import crud_file
from app.schemas.file import File as FileSchema, FileCreate

router = APIRouter()

@router.post("/upload", response_model=FileSchema)
async def upload_file(
    *,
    db: AsyncSession = Depends(deps.get_db),
    file: UploadFile = FastAPIFile(...),
    current_user = Depends(deps.get_current_user)
) -> Any:
    """
    Upload a file, save it to disk (and Supabase if configured), and extract text.
    """
    # 1. Save file to disk (temp)
    local_file_path = await save_upload_file(file)
    final_storage_path = local_file_path
    
    # 2. Extract Text
    text_content = extract_text_from_file(local_file_path, file.content_type)
    
    # 3. Upload to Supabase (Optional)
    try:
        public_url = await upload_to_supabase(local_file_path, file.filename, file.content_type)
        if public_url:
            final_storage_path = public_url
            # Clean up local file
            try:
                os.remove(local_file_path)
            except OSError:
                pass
    except Exception as e:
        print(f"Supabase upload skipped: {e}")

    # 4. Create DB record
    file_in = FileCreate(
        file_name=file.filename,
        file_type=file.content_type,
        storage_path=final_storage_path,
        negotiation_id=None, # Initially not linked to a negotiation
        user_id=current_user.id
    )
    file_record = await crud_file.create(db, obj_in=file_in)
    
    # 5. Ingest text into Pinecone vector store
    if text_content:
        try:
            metadata = {
                "file_id": str(file_record.id),
                "file_name": file.filename,
                "file_type": file.content_type,
                "user_id": current_user.id if current_user else None,
            }
            await ingest_text(text_content, metadata)
        except Exception as e:
            print(f"Vector ingestion failed: {e}")
            # Don't fail the upload if vector ingestion fails
    
    return file_record

@router.get("/", response_model=List[FileSchema])
async def read_files(
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
) -> Any:
    """
    Retrieve all uploaded files.
    """
    return await crud_file.get_all_for_user(db, current_user.id)
