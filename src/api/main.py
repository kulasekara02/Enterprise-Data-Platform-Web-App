"""DataOps Dashboard - FastAPI Application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import structlog

from src.api.config import settings
from src.api.routes import auth, data, jobs, reports, pages
from src.core.database import init_db, close_db

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting DataOps Dashboard", env=settings.ENV)
    await init_db()
    yield
    # Shutdown
    logger.info("Shutting down DataOps Dashboard")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="DataOps Dashboard",
    description="Enterprise Data Platform for data ingestion, validation, and reporting",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(data.router, prefix="/api/data", tags=["Data"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(pages.router, tags=["Pages"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/dashboard/stats")
async def dashboard_stats():
    """Get dashboard statistics."""
    # TODO: Implement actual stats from database
    return {
        "files": {"total": 156, "today": 12, "processing": 2, "failed": 3},
        "records": {"customers": 45230, "orders": 128456},
        "errors": {"total": 234, "today": 15},
        "jobs": {"running": 1, "queued": 3}
    }
