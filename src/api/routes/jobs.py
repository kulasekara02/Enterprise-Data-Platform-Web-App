"""Job management routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from src.core.security import get_current_user, TokenData
from src.core.database import get_db_dependency

router = APIRouter()


class JobResponse(BaseModel):
    """Job response schema."""
    id: int
    job_name: str
    job_type: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class JobCreate(BaseModel):
    """Job creation schema."""
    job_type: str
    parameters: Optional[dict] = None


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: TokenData = Depends(get_current_user),
    db=Depends(get_db_dependency)
):
    """List jobs with optional status filter."""
    where_clause = ""
    params = []

    if status:
        where_clause = "WHERE status = :1"
        params.append(status)

    db.execute(f"""
        SELECT id, job_name, job_type, status, started_at, completed_at, error_message
        FROM jobs
        {where_clause}
        ORDER BY started_at DESC NULLS LAST
        FETCH FIRST {limit} ROWS ONLY
    """, params)

    jobs = []
    for row in db.fetchall():
        jobs.append(JobResponse(
            id=row[0],
            job_name=row[1],
            job_type=row[2],
            status=row[3],
            started_at=row[4],
            completed_at=row[5],
            error_message=row[6]
        ))

    return jobs


@router.post("", response_model=JobResponse)
async def create_job(
    job: JobCreate,
    user: TokenData = Depends(get_current_user),
    db=Depends(get_db_dependency)
):
    """Create and start a new job."""
    import json

    job_name = f"{job.job_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    db.execute("""
        INSERT INTO jobs (job_name, job_type, status, started_by, started_at, parameters)
        VALUES (:1, :2, 'pending', :3, CURRENT_TIMESTAMP, :4)
    """, [job_name, job.job_type, user.user_id, json.dumps(job.parameters) if job.parameters else None])

    # Get the created job
    db.execute("""
        SELECT id, job_name, job_type, status, started_at
        FROM jobs WHERE job_name = :1
    """, [job_name])

    row = db.fetchone()

    # TODO: Trigger Celery task based on job_type
    # if job.job_type == "daily_etl":
    #     from src.workers.tasks.etl_tasks import daily_etl_task
    #     daily_etl_task.delay(row[0])

    return JobResponse(
        id=row[0],
        job_name=row[1],
        job_type=row[2],
        status=row[3],
        started_at=row[4]
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    user: TokenData = Depends(get_current_user),
    db=Depends(get_db_dependency)
):
    """Get job details by ID."""
    db.execute("""
        SELECT id, job_name, job_type, status, started_at, completed_at, error_message
        FROM jobs WHERE id = :1
    """, [job_id])

    row = db.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=row[0],
        job_name=row[1],
        job_type=row[2],
        status=row[3],
        started_at=row[4],
        completed_at=row[5],
        error_message=row[6]
    )


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: int,
    user: TokenData = Depends(get_current_user),
    db=Depends(get_db_dependency)
):
    """Cancel a running job."""
    db.execute("SELECT status FROM jobs WHERE id = :1", [job_id])
    row = db.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    if row[0] not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")

    db.execute("""
        UPDATE jobs
        SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
        WHERE id = :1
    """, [job_id])

    return {"message": "Job cancelled"}
