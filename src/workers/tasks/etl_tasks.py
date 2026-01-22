"""ETL Celery tasks - Extract, Transform, Load operations."""
import logging
from datetime import datetime
from pathlib import Path

from src.workers.celery_app import celery_app
from src.api.config import settings
from src.services.ingest import IngestService
from src.services.validate import DataValidator, ValidationResult, create_customer_validator
from src.services.load import LoadService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_file(self, file_id: int, file_path: str, file_type: str, data_type: str = 'auto'):
    """
    Main ETL task - process uploaded file.

    Args:
        file_id: Database ID of the file record
        file_path: Path to the uploaded file
        file_type: File extension (csv, xlsx, etc.)
        data_type: Type of data (customers, orders, auto)
    """
    import asyncio

    logger.info(f"Starting ETL for file {file_id}: {file_path}")

    try:
        # Update status to processing
        asyncio.run(_update_file_status(file_id, 'processing'))

        # Extract
        ingest = IngestService(file_path, file_type)
        row_count = ingest.get_row_count()

        logger.info(f"File has {row_count} rows")

        # Detect data type if auto
        if data_type == 'auto':
            headers = ingest.get_headers()
            data_type = _detect_data_type(headers)

        # Get appropriate validator
        validator = _get_validator(data_type)

        # Process in batches
        total_valid = 0
        total_errors = 0
        all_errors = []

        for batch_num, batch_df in enumerate(ingest.read_in_batches()):
            logger.info(f"Processing batch {batch_num + 1}")

            # Validate
            result = validator.validate_dataframe(batch_df, start_row=batch_num * settings.BATCH_SIZE + 1)

            total_valid += result.valid_rows
            total_errors += result.error_rows
            all_errors.extend(result.errors[:100])  # Limit stored errors

            # Load valid rows
            if result.valid_rows > 0:
                valid_df = _filter_valid_rows(batch_df, result)
                asyncio.run(_load_data(valid_df, file_id, data_type))

            # Update progress
            progress = min(100, int((batch_num + 1) * settings.BATCH_SIZE / row_count * 100))
            self.update_state(state='PROGRESS', meta={'progress': progress, 'rows_processed': (batch_num + 1) * settings.BATCH_SIZE})

        # Store errors in database
        if all_errors:
            asyncio.run(_store_errors(file_id, all_errors[:500]))  # Limit to 500 errors

        # Update file status
        asyncio.run(_update_file_status(
            file_id,
            'completed',
            row_count=total_valid,
            processed_at=datetime.utcnow()
        ))

        logger.info(f"ETL completed for file {file_id}: {total_valid} valid, {total_errors} errors")

        return {
            'file_id': file_id,
            'status': 'completed',
            'total_rows': row_count,
            'valid_rows': total_valid,
            'error_rows': total_errors
        }

    except Exception as e:
        logger.exception(f"ETL failed for file {file_id}: {e}")

        # Update file status to failed
        import asyncio
        asyncio.run(_update_file_status(file_id, 'failed', error_message=str(e)))

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task
def validate_file(file_id: int, file_path: str, file_type: str, data_type: str) -> dict:
    """
    Validate file without loading - for preview/dry-run.
    """
    logger.info(f"Validating file {file_id}")

    ingest = IngestService(file_path, file_type)
    validator = _get_validator(data_type)

    # Just validate first batch for preview
    for batch_df in ingest.read_in_batches():
        result = validator.validate_dataframe(batch_df)

        return {
            'file_id': file_id,
            'sample_size': len(batch_df),
            'valid_rows': result.valid_rows,
            'error_rows': result.error_rows,
            'error_rate': result.error_rate,
            'sample_errors': [
                {
                    'row': e.row_number,
                    'field': e.field_name,
                    'value': str(e.field_value),
                    'error': e.error_message
                }
                for e in result.errors[:10]
            ]
        }

    return {'file_id': file_id, 'error': 'No data found'}


@celery_app.task
def reprocess_file(file_id: int):
    """Reprocess a failed file."""
    import asyncio

    # Get file info from database
    file_info = asyncio.run(_get_file_info(file_id))

    if not file_info:
        raise ValueError(f"File {file_id} not found")

    # Clear previous errors
    asyncio.run(_clear_file_errors(file_id))

    # Rerun ETL
    return process_file.delay(
        file_id=file_id,
        file_path=file_info['file_path'],
        file_type=file_info['file_type']
    )


def _detect_data_type(headers: list) -> str:
    """Detect data type from column headers."""
    headers_lower = [h.lower() for h in headers]

    customer_indicators = ['customer', 'email', 'phone', 'credit_limit', 'segment']
    order_indicators = ['order', 'amount', 'total', 'quantity', 'product']

    customer_score = sum(1 for h in headers_lower if any(ind in h for ind in customer_indicators))
    order_score = sum(1 for h in headers_lower if any(ind in h for ind in order_indicators))

    if customer_score > order_score:
        return 'customers'
    elif order_score > customer_score:
        return 'orders'
    else:
        return 'generic'


def _get_validator(data_type: str) -> DataValidator:
    """Get appropriate validator for data type."""
    if data_type == 'customers':
        return create_customer_validator()
    elif data_type == 'orders':
        from src.services.validate import create_order_validator
        return create_order_validator()
    else:
        # Generic validator - just check for required fields
        return DataValidator()


def _filter_valid_rows(df, result: ValidationResult):
    """Filter DataFrame to only include valid rows."""
    error_rows = set(e.row_number for e in result.errors)
    # Adjust for 0-based indexing
    return df[~df.index.isin([r - 1 for r in error_rows])]


async def _update_file_status(file_id: int, status: str, **kwargs):
    """Update file status in database."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    set_clauses = ['status = :status']
    params = {'file_id': file_id, 'status': status}

    if 'row_count' in kwargs:
        set_clauses.append('row_count = :row_count')
        params['row_count'] = kwargs['row_count']

    if 'processed_at' in kwargs:
        set_clauses.append('processed_at = :processed_at')
        params['processed_at'] = kwargs['processed_at']

    if 'error_message' in kwargs:
        set_clauses.append('error_message = :error_message')
        params['error_message'] = kwargs['error_message'][:1000]  # Truncate

    sql = f"UPDATE data_files SET {', '.join(set_clauses)} WHERE id = :file_id"

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(sql, params)
            await conn.commit()


async def _load_data(df, file_id: int, data_type: str):
    """Load validated data into appropriate table."""
    if data_type == 'customers':
        from src.services.load import load_customers
        await load_customers(df, file_id)
    elif data_type == 'orders':
        from src.services.load import load_orders
        await load_orders(df, file_id)
    # For generic data, would need custom handling


async def _store_errors(file_id: int, errors: list):
    """Store validation errors in database."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    sql = """
        INSERT INTO data_errors (source_file_id, row_number, error_type, error_message, field_name, field_value, raw_data)
        VALUES (:file_id, :row_number, :error_type, :error_message, :field_name, :field_value, :raw_data)
    """

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for error in errors:
                await cursor.execute(sql, {
                    'file_id': file_id,
                    'row_number': error.row_number,
                    'error_type': error.error_type.value,
                    'error_message': error.error_message[:1000],
                    'field_name': error.field_name,
                    'field_value': str(error.field_value)[:500] if error.field_value else None,
                    'raw_data': error.raw_data[:4000] if error.raw_data else None
                })
            await conn.commit()


async def _get_file_info(file_id: int) -> dict:
    """Get file info from database."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT filename, file_type FROM data_files WHERE id = :id",
                {'id': file_id}
            )
            row = await cursor.fetchone()

            if row:
                return {
                    'file_path': str(Path(settings.UPLOAD_DIR) / row[0]),
                    'file_type': row[1]
                }
    return None


async def _clear_file_errors(file_id: int):
    """Clear previous errors for a file."""
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM data_errors WHERE source_file_id = :file_id",
                {'file_id': file_id}
            )
            await conn.commit()
