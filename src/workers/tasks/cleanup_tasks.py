"""Cleanup and maintenance Celery tasks."""
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

from src.workers.celery_app import celery_app
from src.api.config import settings

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_old_files():
    """
    Clean up old processed files.
    Scheduled to run daily at 2 AM.
    """
    import asyncio

    logger.info("Starting file cleanup task")

    retention_days = asyncio.run(_get_retention_days())
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    stats = {
        'files_deleted': 0,
        'space_freed_mb': 0,
        'errors': []
    }

    # Get old completed files
    old_files = asyncio.run(_get_old_files(cutoff_date))

    for file_info in old_files:
        try:
            file_path = Path(settings.UPLOAD_DIR) / file_info['filename']

            if file_path.exists():
                file_size = file_path.stat().st_size
                file_path.unlink()
                stats['files_deleted'] += 1
                stats['space_freed_mb'] += file_size / (1024 * 1024)
                logger.info(f"Deleted file: {file_path}")

            # Update database record
            asyncio.run(_mark_file_archived(file_info['id']))

        except Exception as e:
            logger.error(f"Error deleting file {file_info['filename']}: {e}")
            stats['errors'].append({
                'file': file_info['filename'],
                'error': str(e)
            })

    logger.info(f"Cleanup completed: {stats['files_deleted']} files, {stats['space_freed_mb']:.2f} MB freed")

    return stats


@celery_app.task
def cleanup_old_errors():
    """Clean up old error records to prevent database bloat."""
    import asyncio

    logger.info("Starting error cleanup task")

    # Keep errors for 30 days
    cutoff_date = datetime.now() - timedelta(days=30)

    deleted_count = asyncio.run(_delete_old_errors(cutoff_date))

    logger.info(f"Deleted {deleted_count} old error records")

    return {'deleted_errors': deleted_count}


@celery_app.task
def cleanup_old_audit_logs():
    """Clean up old audit log entries."""
    import asyncio

    logger.info("Starting audit log cleanup task")

    # Keep audit logs for 90 days
    cutoff_date = datetime.now() - timedelta(days=90)

    deleted_count = asyncio.run(_delete_old_audit_logs(cutoff_date))

    logger.info(f"Deleted {deleted_count} old audit log entries")

    return {'deleted_logs': deleted_count}


@celery_app.task
def cleanup_temp_files():
    """Clean up temporary files."""
    logger.info("Starting temp file cleanup")

    temp_dir = Path(settings.UPLOAD_DIR) / 'temp'

    if not temp_dir.exists():
        return {'files_deleted': 0}

    stats = {'files_deleted': 0, 'space_freed_mb': 0}

    # Delete files older than 1 hour
    cutoff_time = datetime.now() - timedelta(hours=1)

    for file_path in temp_dir.iterdir():
        try:
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                if mtime < cutoff_time:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    stats['files_deleted'] += 1
                    stats['space_freed_mb'] += file_size / (1024 * 1024)

        except Exception as e:
            logger.error(f"Error cleaning temp file {file_path}: {e}")

    logger.info(f"Temp cleanup: {stats['files_deleted']} files deleted")

    return stats


@celery_app.task
def vacuum_database():
    """
    Perform database maintenance operations.
    This task gathers statistics and performs maintenance on Oracle tables.
    """
    import asyncio

    logger.info("Starting database maintenance")

    try:
        asyncio.run(_gather_table_stats())
        logger.info("Database maintenance completed")
        return {'status': 'success'}

    except Exception as e:
        logger.error(f"Database maintenance failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@celery_app.task
def check_disk_space():
    """Check available disk space and alert if low."""
    import shutil

    upload_dir = Path(settings.UPLOAD_DIR)

    total, used, free = shutil.disk_usage(upload_dir)

    free_percent = (free / total) * 100

    result = {
        'total_gb': total / (1024**3),
        'used_gb': used / (1024**3),
        'free_gb': free / (1024**3),
        'free_percent': free_percent
    }

    if free_percent < 10:
        logger.warning(f"Low disk space: {free_percent:.1f}% free")
        result['alert'] = 'LOW_DISK_SPACE'
    elif free_percent < 20:
        logger.info(f"Disk space warning: {free_percent:.1f}% free")
        result['warning'] = 'DISK_SPACE_WARNING'

    return result


@celery_app.task
def generate_health_report() -> Dict[str, Any]:
    """Generate system health report."""
    import asyncio
    import shutil

    logger.info("Generating health report")

    # Disk space
    upload_dir = Path(settings.UPLOAD_DIR)
    total, used, free = shutil.disk_usage(upload_dir)

    # Database stats
    db_stats = asyncio.run(_get_database_stats())

    # File stats
    file_stats = asyncio.run(_get_file_stats())

    return {
        'timestamp': datetime.utcnow().isoformat(),
        'disk': {
            'total_gb': round(total / (1024**3), 2),
            'used_gb': round(used / (1024**3), 2),
            'free_gb': round(free / (1024**3), 2),
            'free_percent': round((free / total) * 100, 1)
        },
        'database': db_stats,
        'files': file_stats
    }


# Helper functions

async def _get_retention_days() -> int:
    """Get file retention days from config."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT config_value FROM config WHERE config_key = 'retention_days'"
            )
            row = await cursor.fetchone()
            return int(row[0]) if row else 90


async def _get_old_files(cutoff_date: datetime) -> list:
    """Get list of files older than cutoff date."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("""
                SELECT id, filename
                FROM data_files
                WHERE status = 'completed'
                AND processed_at < :cutoff
            """, {'cutoff': cutoff_date})

            rows = await cursor.fetchall()
            return [{'id': row[0], 'filename': row[1]} for row in rows]


async def _mark_file_archived(file_id: int):
    """Mark file as archived in database."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE data_files SET status = 'archived' WHERE id = :id",
                {'id': file_id}
            )
            await conn.commit()


async def _delete_old_errors(cutoff_date: datetime) -> int:
    """Delete error records older than cutoff date."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM data_errors WHERE created_at < :cutoff",
                {'cutoff': cutoff_date}
            )
            deleted = cursor.rowcount
            await conn.commit()
            return deleted


async def _delete_old_audit_logs(cutoff_date: datetime) -> int:
    """Delete audit logs older than cutoff date."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM audit_log WHERE created_at < :cutoff",
                {'cutoff': cutoff_date}
            )
            deleted = cursor.rowcount
            await conn.commit()
            return deleted


async def _gather_table_stats():
    """Gather Oracle table statistics for query optimization."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    tables = ['users', 'data_files', 'customers', 'orders', 'data_errors', 'jobs', 'audit_log']

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for table in tables:
                await cursor.execute(f"""
                    BEGIN
                        DBMS_STATS.GATHER_TABLE_STATS(
                            ownname => USER,
                            tabname => '{table.upper()}',
                            estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE
                        );
                    END;
                """)
            await conn.commit()


async def _get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Table row counts
            await cursor.execute("""
                SELECT
                    (SELECT COUNT(*) FROM users) as users,
                    (SELECT COUNT(*) FROM data_files) as files,
                    (SELECT COUNT(*) FROM customers) as customers,
                    (SELECT COUNT(*) FROM orders) as orders,
                    (SELECT COUNT(*) FROM data_errors) as errors
                FROM dual
            """)
            row = await cursor.fetchone()

            return {
                'users': row[0],
                'files': row[1],
                'customers': row[2],
                'orders': row[3],
                'errors': row[4]
            }


async def _get_file_stats() -> Dict[str, Any]:
    """Get file statistics."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("""
                SELECT
                    status,
                    COUNT(*) as count,
                    SUM(file_size) as total_size
                FROM data_files
                GROUP BY status
            """)
            rows = await cursor.fetchall()

            return {
                row[0]: {
                    'count': row[1],
                    'total_size_mb': round((row[2] or 0) / (1024 * 1024), 2)
                }
                for row in rows
            }
