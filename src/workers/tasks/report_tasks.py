"""Report generation Celery tasks."""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

import pandas as pd

from src.workers.celery_app import celery_app
from src.api.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def generate_weekly_report(self):
    """
    Generate weekly summary report.
    Scheduled to run every Monday at 6 AM.
    """
    import asyncio

    logger.info("Starting weekly report generation")

    try:
        report_data = asyncio.run(_gather_weekly_stats())

        # Generate report file
        report_path = _generate_report_file(report_data, 'weekly')

        # Store report record
        report_id = asyncio.run(_save_report_record(
            name=f"Weekly Report - {datetime.now().strftime('%Y-%m-%d')}",
            report_type='weekly',
            file_path=report_path
        ))

        logger.info(f"Weekly report generated: {report_path}")

        return {
            'report_id': report_id,
            'file_path': report_path,
            'generated_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.exception(f"Weekly report failed: {e}")
        raise


@celery_app.task(bind=True)
def generate_custom_report(self, report_type: str, parameters: Dict[str, Any], user_id: int):
    """
    Generate custom report based on parameters.
    """
    import asyncio

    logger.info(f"Generating {report_type} report for user {user_id}")

    try:
        if report_type == 'file_summary':
            data = asyncio.run(_generate_file_summary_report(parameters))
        elif report_type == 'error_analysis':
            data = asyncio.run(_generate_error_analysis_report(parameters))
        elif report_type == 'customer_stats':
            data = asyncio.run(_generate_customer_stats_report(parameters))
        else:
            raise ValueError(f"Unknown report type: {report_type}")

        # Generate file
        report_path = _generate_report_file(data, report_type)

        # Store record
        report_id = asyncio.run(_save_report_record(
            name=f"{report_type.replace('_', ' ').title()} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            report_type=report_type,
            file_path=report_path,
            user_id=user_id,
            parameters=parameters
        ))

        return {
            'report_id': report_id,
            'file_path': report_path,
            'report_type': report_type
        }

    except Exception as e:
        logger.exception(f"Custom report generation failed: {e}")
        raise


@celery_app.task
def export_data(table: str, filters: Dict[str, Any], format: str, user_id: int):
    """
    Export data from a table to file.
    """
    import asyncio

    logger.info(f"Exporting {table} data for user {user_id}")

    try:
        # Get data
        df = asyncio.run(_fetch_table_data(table, filters))

        # Generate export file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"export_{table}_{timestamp}"

        reports_dir = Path(settings.UPLOAD_DIR) / 'reports'
        reports_dir.mkdir(exist_ok=True)

        if format == 'csv':
            file_path = reports_dir / f"{filename}.csv"
            df.to_csv(file_path, index=False)
        elif format == 'xlsx':
            file_path = reports_dir / f"{filename}.xlsx"
            df.to_excel(file_path, index=False)
        elif format == 'json':
            file_path = reports_dir / f"{filename}.json"
            df.to_json(file_path, orient='records', indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

        return {
            'file_path': str(file_path),
            'row_count': len(df),
            'format': format
        }

    except Exception as e:
        logger.exception(f"Data export failed: {e}")
        raise


async def _gather_weekly_stats() -> Dict[str, Any]:
    """Gather statistics for weekly report."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    week_ago = datetime.now() - timedelta(days=7)

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # File statistics
            await cursor.execute("""
                SELECT
                    COUNT(*) as total_files,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(row_count) as total_rows
                FROM data_files
                WHERE uploaded_at >= :week_ago
            """, {'week_ago': week_ago})

            file_row = await cursor.fetchone()

            # Error statistics
            await cursor.execute("""
                SELECT error_type, COUNT(*) as count
                FROM data_errors
                WHERE created_at >= :week_ago
                GROUP BY error_type
                ORDER BY count DESC
            """, {'week_ago': week_ago})

            error_rows = await cursor.fetchall()

            # Daily breakdown
            await cursor.execute("""
                SELECT
                    TRUNC(uploaded_at) as upload_date,
                    COUNT(*) as file_count
                FROM data_files
                WHERE uploaded_at >= :week_ago
                GROUP BY TRUNC(uploaded_at)
                ORDER BY upload_date
            """, {'week_ago': week_ago})

            daily_rows = await cursor.fetchall()

    return {
        'period': {
            'start': week_ago.isoformat(),
            'end': datetime.now().isoformat()
        },
        'files': {
            'total': file_row[0] or 0,
            'completed': file_row[1] or 0,
            'failed': file_row[2] or 0,
            'total_rows': file_row[3] or 0
        },
        'errors_by_type': {row[0]: row[1] for row in error_rows},
        'daily_uploads': [{'date': str(row[0]), 'count': row[1]} for row in daily_rows]
    }


async def _generate_file_summary_report(params: Dict) -> Dict[str, Any]:
    """Generate file summary report."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    start_date = params.get('start_date')
    end_date = params.get('end_date')

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = """
                SELECT
                    f.id, f.original_name, f.file_type, f.status,
                    f.row_count, f.uploaded_at, u.username
                FROM data_files f
                LEFT JOIN users u ON f.uploaded_by = u.id
                WHERE 1=1
            """
            binds = {}

            if start_date:
                sql += " AND f.uploaded_at >= :start_date"
                binds['start_date'] = start_date
            if end_date:
                sql += " AND f.uploaded_at <= :end_date"
                binds['end_date'] = end_date

            sql += " ORDER BY f.uploaded_at DESC"

            await cursor.execute(sql, binds)
            rows = await cursor.fetchall()

    return {
        'title': 'File Summary Report',
        'generated_at': datetime.now().isoformat(),
        'parameters': params,
        'data': [
            {
                'id': row[0],
                'filename': row[1],
                'type': row[2],
                'status': row[3],
                'rows': row[4],
                'uploaded_at': str(row[5]),
                'uploaded_by': row[6]
            }
            for row in rows
        ]
    }


async def _generate_error_analysis_report(params: Dict) -> Dict[str, Any]:
    """Generate error analysis report."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Error summary by type
            await cursor.execute("""
                SELECT error_type, COUNT(*) as count,
                       COUNT(DISTINCT source_file_id) as affected_files
                FROM data_errors
                GROUP BY error_type
                ORDER BY count DESC
            """)
            error_summary = await cursor.fetchall()

            # Most common error fields
            await cursor.execute("""
                SELECT field_name, COUNT(*) as count
                FROM data_errors
                WHERE field_name IS NOT NULL
                GROUP BY field_name
                ORDER BY count DESC
                FETCH FIRST 10 ROWS ONLY
            """)
            field_errors = await cursor.fetchall()

            # Recent error samples
            await cursor.execute("""
                SELECT e.error_type, e.field_name, e.error_message,
                       e.field_value, f.original_name
                FROM data_errors e
                JOIN data_files f ON e.source_file_id = f.id
                ORDER BY e.created_at DESC
                FETCH FIRST 50 ROWS ONLY
            """)
            recent_errors = await cursor.fetchall()

    return {
        'title': 'Error Analysis Report',
        'generated_at': datetime.now().isoformat(),
        'summary': [
            {'type': row[0], 'count': row[1], 'affected_files': row[2]}
            for row in error_summary
        ],
        'top_error_fields': [
            {'field': row[0], 'count': row[1]}
            for row in field_errors
        ],
        'recent_samples': [
            {
                'type': row[0],
                'field': row[1],
                'message': row[2],
                'value': row[3],
                'file': row[4]
            }
            for row in recent_errors
        ]
    }


async def _generate_customer_stats_report(params: Dict) -> Dict[str, Any]:
    """Generate customer statistics report."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Customer count by country
            await cursor.execute("""
                SELECT country, COUNT(*) as count
                FROM customers
                WHERE country IS NOT NULL
                GROUP BY country
                ORDER BY count DESC
            """)
            by_country = await cursor.fetchall()

            # Customer count by segment
            await cursor.execute("""
                SELECT segment, COUNT(*) as count
                FROM customers
                WHERE segment IS NOT NULL
                GROUP BY segment
                ORDER BY count DESC
            """)
            by_segment = await cursor.fetchall()

            # Credit limit statistics
            await cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    AVG(credit_limit) as avg_limit,
                    MAX(credit_limit) as max_limit,
                    MIN(credit_limit) as min_limit
                FROM customers
                WHERE credit_limit IS NOT NULL
            """)
            credit_stats = await cursor.fetchone()

    return {
        'title': 'Customer Statistics Report',
        'generated_at': datetime.now().isoformat(),
        'by_country': [{'country': row[0], 'count': row[1]} for row in by_country],
        'by_segment': [{'segment': row[0], 'count': row[1]} for row in by_segment],
        'credit_statistics': {
            'total_customers': credit_stats[0],
            'average_limit': float(credit_stats[1]) if credit_stats[1] else 0,
            'max_limit': float(credit_stats[2]) if credit_stats[2] else 0,
            'min_limit': float(credit_stats[3]) if credit_stats[3] else 0
        }
    }


def _generate_report_file(data: Dict[str, Any], report_type: str) -> str:
    """Generate report file from data."""
    import json

    reports_dir = Path(settings.UPLOAD_DIR) / 'reports'
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"report_{report_type}_{timestamp}.json"
    file_path = reports_dir / filename

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    return str(file_path)


async def _save_report_record(name: str, report_type: str, file_path: str,
                              user_id: int = None, parameters: Dict = None) -> int:
    """Save report record to database."""
    import json
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO reports (report_name, report_type, file_path, generated_by, parameters)
                VALUES (:name, :type, :path, :user_id, :params)
                RETURNING id INTO :report_id
            """, {
                'name': name,
                'type': report_type,
                'path': file_path,
                'user_id': user_id,
                'params': json.dumps(parameters) if parameters else None,
                'report_id': cursor.var(int)
            })
            await conn.commit()

            return cursor.getvalue(0)[0]


async def _fetch_table_data(table: str, filters: Dict) -> pd.DataFrame:
    """Fetch data from table with filters."""
    from src.core.database import get_db_pool

    # Whitelist of allowed tables for security
    allowed_tables = {'customers', 'orders', 'data_files', 'data_errors'}

    if table not in allowed_tables:
        raise ValueError(f"Table {table} not allowed for export")

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Build query with filters
            sql = f"SELECT * FROM {table}"

            where_clauses = []
            binds = {}

            for key, value in filters.items():
                where_clauses.append(f"{key} = :{key}")
                binds[key] = value

            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)

            await cursor.execute(sql, binds)

            columns = [col[0].lower() for col in cursor.description]
            rows = await cursor.fetchall()

            return pd.DataFrame(rows, columns=columns)
