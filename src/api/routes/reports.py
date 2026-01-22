"""Report generation routes."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel
from src.core.security import get_current_user, TokenData
from src.core.database import get_db_dependency

router = APIRouter()


class ReportRequest(BaseModel):
    """Report generation request."""
    report_type: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ReportResponse(BaseModel):
    """Report response schema."""
    id: int
    report_name: str
    report_type: str
    generated_at: datetime
    file_path: Optional[str] = None


@router.get("")
async def list_reports(
    user: TokenData = Depends(get_current_user),
    db=Depends(get_db_dependency)
):
    """List generated reports."""
    db.execute("""
        SELECT id, report_name, report_type, generated_at, file_path
        FROM reports
        ORDER BY generated_at DESC
        FETCH FIRST 50 ROWS ONLY
    """)

    reports = []
    for row in db.fetchall():
        reports.append(ReportResponse(
            id=row[0],
            report_name=row[1],
            report_type=row[2],
            generated_at=row[3],
            file_path=row[4]
        ))

    return reports


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    user: TokenData = Depends(get_current_user),
    db=Depends(get_db_dependency)
):
    """Generate a new report."""
    import json

    report_name = f"{request.report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Insert report record
    db.execute("""
        INSERT INTO reports (report_name, report_type, parameters, generated_by)
        VALUES (:1, :2, :3, :4)
    """, [
        report_name,
        request.report_type,
        json.dumps({
            "start_date": str(request.start_date) if request.start_date else None,
            "end_date": str(request.end_date) if request.end_date else None
        }),
        user.user_id
    ])

    # Get created report
    db.execute("""
        SELECT id, report_name, report_type, generated_at
        FROM reports WHERE report_name = :1
    """, [report_name])

    row = db.fetchone()

    # TODO: Trigger Celery task to generate report
    # from src.workers.tasks.report_tasks import generate_report_task
    # generate_report_task.delay(row[0])

    return ReportResponse(
        id=row[0],
        report_name=row[1],
        report_type=row[2],
        generated_at=row[3]
    )


@router.get("/{report_id}")
async def get_report(
    report_id: int,
    user: TokenData = Depends(get_current_user),
    db=Depends(get_db_dependency)
):
    """Get report details."""
    db.execute("""
        SELECT id, report_name, report_type, generated_at, file_path
        FROM reports WHERE id = :1
    """, [report_id])

    row = db.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResponse(
        id=row[0],
        report_name=row[1],
        report_type=row[2],
        generated_at=row[3],
        file_path=row[4]
    )
