"""Celery application configuration."""
from celery import Celery
from celery.schedules import crontab
from src.api.config import settings

# Create Celery app
celery_app = Celery(
    "dataops",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "src.workers.tasks.etl_tasks",
        "src.workers.tasks.report_tasks",
        "src.workers.tasks.cleanup_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

# Beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    "daily-cleanup": {
        "task": "src.workers.tasks.cleanup_tasks.cleanup_old_files",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
    "weekly-report": {
        "task": "src.workers.tasks.report_tasks.generate_weekly_report",
        "schedule": crontab(hour=6, minute=0, day_of_week=1),  # Monday 6 AM
    },
}
