"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Optional, List, Any, Dict
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ==============================================
# Enums
# ==============================================

class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class FileStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ==============================================
# Authentication Schemas
# ==============================================

class LoginRequest(BaseModel):
    """Login request body."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class RegisterRequest(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.VIEWER


# ==============================================
# User Schemas
# ==============================================

class UserBase(BaseModel):
    """Base user schema."""
    username: str
    email: EmailStr
    role: UserRole


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    """User response schema."""
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


# ==============================================
# File Schemas
# ==============================================

class FileBase(BaseModel):
    """Base file schema."""
    original_name: str
    file_type: str


class FileResponse(FileBase):
    """File response schema."""
    id: int
    filename: str
    file_size: int
    row_count: Optional[int] = None
    status: FileStatus
    uploaded_by: int
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FileListResponse(BaseModel):
    """Paginated file list response."""
    items: List[FileResponse]
    total: int
    page: int
    page_size: int


class FilePreviewResponse(BaseModel):
    """File preview response."""
    headers: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int


class FileUploadResponse(BaseModel):
    """File upload response."""
    id: int
    filename: str
    status: FileStatus
    task_id: Optional[str] = None
    message: str


# ==============================================
# Validation Schemas
# ==============================================

class ValidationErrorItem(BaseModel):
    """Single validation error."""
    row: int
    field: str
    value: Optional[str] = None
    error: str
    error_type: str


class ValidationResultResponse(BaseModel):
    """Validation result response."""
    total_rows: int
    valid_rows: int
    error_rows: int
    error_rate: float
    errors: List[ValidationErrorItem]


# ==============================================
# Job Schemas
# ==============================================

class JobBase(BaseModel):
    """Base job schema."""
    job_name: str
    job_type: str


class JobResponse(JobBase):
    """Job response schema."""
    id: int
    status: JobStatus
    started_by: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parameters: Optional[str] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    progress: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    """Paginated job list response."""
    items: List[JobResponse]
    total: int
    page: int
    page_size: int


class JobStatsResponse(BaseModel):
    """Job statistics response."""
    running: int
    queued: int
    completed_24h: int
    failed_24h: int


# ==============================================
# Report Schemas
# ==============================================

class ReportGenerateRequest(BaseModel):
    """Report generation request."""
    report_type: str
    parameters: Optional[Dict[str, Any]] = None


class ReportResponse(BaseModel):
    """Report response schema."""
    id: int
    report_name: str
    report_type: str
    file_path: Optional[str] = None
    generated_by: Optional[int] = None
    generated_at: datetime
    parameters: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReportListResponse(BaseModel):
    """Paginated report list response."""
    items: List[ReportResponse]
    total: int


class ExportRequest(BaseModel):
    """Data export request."""
    table: str
    format: str = Field(..., pattern="^(csv|xlsx|json)$")
    filters: Optional[Dict[str, Any]] = None


class ExportResponse(BaseModel):
    """Data export response."""
    file_path: str
    row_count: int
    format: str


# ==============================================
# Dashboard Schemas
# ==============================================

class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response."""
    files: Dict[str, int]
    records: Dict[str, int]
    errors: Dict[str, int]
    jobs: Dict[str, int]


# ==============================================
# Error Schemas
# ==============================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    detail: str
    errors: List[Dict[str, Any]]


# ==============================================
# Pagination
# ==============================================

class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


# Resolve forward references
TokenResponse.model_rebuild()
