"""Data management routes."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import Optional
from datetime import datetime
import os
import uuid
from pydantic import BaseModel
from src.core.security import get_current_user, TokenData
from src.core.database import get_db_dependency
from src.api.config import settings

router = APIRouter()


class FileResponse(BaseModel):
    """File response schema."""
    id: int
    filename: str
    original_name: str
    file_type: str
    file_size: int
    status: str
    row_count: Optional[int] = None
    uploaded_at: datetime


class FileListResponse(BaseModel):
    """File list response."""
    items: list[FileResponse]
    total: int
    page: int
    pages: int


@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    user: TokenData = Depends(get_current_user),
    db=Depends(get_db_dependency)
):
    """Upload a data file (CSV or JSON)."""
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    extension = file.filename.split(".")[-1].lower()
    if extension not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="Only CSV and JSON files allowed")

    # Check file size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    new_filename = f"{timestamp}_{unique_id}_{file.filename}"

    # Save file
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, new_filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # Insert metadata to database
    db.execute("""
        INSERT INTO data_files (filename, original_name, file_type, file_size, uploaded_by, status)
        VALUES (:1, :2, :3, :4, :5, 'uploaded')
        RETURNING id INTO :6
    """, [new_filename, file.filename, extension, len(content), user.user_id, db.var(int)])

    file_id = db.getvalue(0)

    return FileResponse(
        id=file_id,
        filename=new_filename,
        original_name=file.filename,
        file_type=extension,
        file_size=len(content),
        status="uploaded",
        uploaded_at=datetime.now()
    )


@router.get("/files", response_model=FileListResponse)
async def list_files(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: TokenData = Depends(get_current_user),
    db=Depends(get_db_dependency)
):
    """List uploaded files with filtering and pagination."""
    offset = (page - 1) * limit

    # Build query
    where_clause = "WHERE 1=1"
    params = []

    if status:
        where_clause += " AND status = :1"
        params.append(status)

    # Get total count
    db.execute(f"SELECT COUNT(*) FROM data_files {where_clause}", params)
    total = db.fetchone()[0]

    # Get files
    db.execute(f"""
        SELECT id, filename, original_name, file_type, file_size, status, row_count, uploaded_at
        FROM data_files
        {where_clause}
        ORDER BY uploaded_at DESC
        OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY
    """, params)

    files = []
    for row in db.fetchall():
        files.append(FileResponse(
            id=row[0],
            filename=row[1],
            original_name=row[2],
            file_type=row[3],
            file_size=row[4],
            status=row[5],
            row_count=row[6],
            uploaded_at=row[7]
        ))

    return FileListResponse(
        items=files,
        total=total,
        page=page,
        pages=(total + limit - 1) // limit
    )


@router.get("/files/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: int,
    user: TokenData = Depends(get_current_user),
    db=Depends(get_db_dependency)
):
    """Get file details by ID."""
    db.execute("""
        SELECT id, filename, original_name, file_type, file_size, status, row_count, uploaded_at
        FROM data_files WHERE id = :1
    """, [file_id])

    row = db.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        id=row[0],
        filename=row[1],
        original_name=row[2],
        file_type=row[3],
        file_size=row[4],
        status=row[5],
        row_count=row[6],
        uploaded_at=row[7]
    )


@router.post("/files/{file_id}/process")
async def process_file(
    file_id: int,
    user: TokenData = Depends(get_current_user),
    db=Depends(get_db_dependency)
):
    """Start processing a file (triggers Celery task)."""
    # Check file exists
    db.execute("SELECT id, status FROM data_files WHERE id = :1", [file_id])
    row = db.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    if row[1] == "processing":
        raise HTTPException(status_code=400, detail="File already processing")

    # Update status
    db.execute("UPDATE data_files SET status = 'processing' WHERE id = :1", [file_id])

    # TODO: Trigger Celery task
    # from src.workers.tasks.etl_tasks import process_file_task
    # job = process_file_task.delay(file_id)

    return {"message": "Processing started", "file_id": file_id}


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    user: TokenData = Depends(get_current_user),
    db=Depends(get_db_dependency)
):
    """Delete a file."""
    # Check permission (admin or owner)
    db.execute("SELECT filename, uploaded_by FROM data_files WHERE id = :1", [file_id])
    row = db.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    if user.role != "admin" and row[1] != user.user_id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Delete physical file
    file_path = os.path.join(settings.UPLOAD_DIR, row[0])
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete from database
    db.execute("DELETE FROM data_files WHERE id = :1", [file_id])

    return {"message": "File deleted"}
