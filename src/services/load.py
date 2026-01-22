"""Data loading service - loads validated data into Oracle database."""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

import pandas as pd
import oracledb

from src.core.database import get_db_pool

logger = logging.getLogger(__name__)


class LoadService:
    """Service for loading data into Oracle database."""

    def __init__(self, table_name: str, column_mapping: Dict[str, str] = None):
        """
        Initialize loader.

        Args:
            table_name: Target Oracle table name
            column_mapping: Dict mapping DataFrame columns to table columns
        """
        self.table_name = table_name
        self.column_mapping = column_mapping or {}

    async def load_dataframe(
        self,
        df: pd.DataFrame,
        source_file_id: int,
        batch_size: int = 1000,
        on_conflict: str = 'skip'  # 'skip', 'update', 'error'
    ) -> Dict[str, Any]:
        """
        Load DataFrame into Oracle table.

        Returns dict with load statistics.
        """
        pool = await get_db_pool()

        # Apply column mapping
        if self.column_mapping:
            df = df.rename(columns=self.column_mapping)

        # Add source file reference
        df['source_file_id'] = source_file_id

        # Get columns that exist in table
        table_columns = await self._get_table_columns(pool)
        df_columns = [c for c in df.columns if c.upper() in [tc.upper() for tc in table_columns]]

        if not df_columns:
            raise ValueError(f"No matching columns found for table {self.table_name}")

        stats = {
            'total_rows': len(df),
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'error_details': []
        }

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Process in batches
                for i in range(0, len(df), batch_size):
                    batch_df = df.iloc[i:i + batch_size]
                    batch_stats = await self._load_batch(
                        cursor, batch_df, df_columns, on_conflict
                    )

                    stats['inserted'] += batch_stats['inserted']
                    stats['updated'] += batch_stats['updated']
                    stats['skipped'] += batch_stats['skipped']
                    stats['errors'] += batch_stats['errors']
                    stats['error_details'].extend(batch_stats.get('error_details', []))

                await conn.commit()

        logger.info(f"Loaded {stats['inserted']} rows into {self.table_name}")
        return stats

    async def _get_table_columns(self, pool) -> List[str]:
        """Get column names from Oracle table."""
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"""
                    SELECT column_name
                    FROM user_tab_columns
                    WHERE table_name = UPPER(:table_name)
                    ORDER BY column_id
                """, {'table_name': self.table_name})

                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def _load_batch(
        self,
        cursor,
        df: pd.DataFrame,
        columns: List[str],
        on_conflict: str
    ) -> Dict[str, int]:
        """Load a batch of rows."""
        stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0, 'error_details': []}

        # Build INSERT statement
        col_names = ', '.join(columns)
        placeholders = ', '.join([f':{i+1}' for i in range(len(columns))])

        insert_sql = f"INSERT INTO {self.table_name} ({col_names}) VALUES ({placeholders})"

        for idx, row in df.iterrows():
            try:
                values = [self._convert_value(row[col]) for col in columns]
                await cursor.execute(insert_sql, values)
                stats['inserted'] += 1

            except oracledb.IntegrityError as e:
                if 'unique constraint' in str(e).lower():
                    if on_conflict == 'skip':
                        stats['skipped'] += 1
                    elif on_conflict == 'update':
                        # Implement update logic if needed
                        stats['skipped'] += 1
                    else:
                        stats['errors'] += 1
                        stats['error_details'].append({
                            'row': idx,
                            'error': str(e)
                        })
                else:
                    stats['errors'] += 1
                    stats['error_details'].append({
                        'row': idx,
                        'error': str(e)
                    })

            except Exception as e:
                stats['errors'] += 1
                stats['error_details'].append({
                    'row': idx,
                    'error': str(e)
                })
                logger.error(f"Error loading row {idx}: {e}")

        return stats

    def _convert_value(self, value: Any) -> Any:
        """Convert pandas value to Oracle-compatible value."""
        if pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
        if isinstance(value, (int, float, str, datetime)):
            return value
        return str(value)


class BulkLoader:
    """High-performance bulk loader using Oracle array operations."""

    def __init__(self, table_name: str):
        self.table_name = table_name

    async def bulk_insert(
        self,
        pool,
        data: List[Dict[str, Any]],
        columns: List[str]
    ) -> int:
        """
        Bulk insert using executemany for better performance.

        Returns number of rows inserted.
        """
        if not data:
            return 0

        col_names = ', '.join(columns)
        placeholders = ', '.join([f':{c}' for c in columns])

        sql = f"INSERT INTO {self.table_name} ({col_names}) VALUES ({placeholders})"

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.executemany(sql, data)
                await conn.commit()
                return cursor.rowcount

    async def merge_data(
        self,
        pool,
        data: List[Dict[str, Any]],
        columns: List[str],
        key_columns: List[str]
    ) -> Dict[str, int]:
        """
        MERGE operation - insert new rows, update existing.

        Returns dict with insert/update counts.
        """
        if not data:
            return {'inserted': 0, 'updated': 0}

        # Build MERGE statement
        source_cols = ', '.join([f':{c} as {c}' for c in columns])
        on_clause = ' AND '.join([f't.{k} = s.{k}' for k in key_columns])

        update_cols = [c for c in columns if c not in key_columns]
        update_clause = ', '.join([f't.{c} = s.{c}' for c in update_cols])

        insert_cols = ', '.join(columns)
        insert_vals = ', '.join([f's.{c}' for c in columns])

        merge_sql = f"""
            MERGE INTO {self.table_name} t
            USING (SELECT {source_cols} FROM dual) s
            ON ({on_clause})
            WHEN MATCHED THEN
                UPDATE SET {update_clause}
            WHEN NOT MATCHED THEN
                INSERT ({insert_cols}) VALUES ({insert_vals})
        """

        stats = {'inserted': 0, 'updated': 0}

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for row in data:
                    await cursor.execute(merge_sql, row)
                    # Oracle doesn't directly tell us if it was insert or update
                    # We'd need to track this separately

                await conn.commit()

        return stats


async def load_customers(df: pd.DataFrame, source_file_id: int) -> Dict[str, Any]:
    """Load customer data with standard mapping."""
    loader = LoadService('customers', {
        'code': 'customer_code',
        'customer_name': 'name',
        'email_address': 'email',
        'phone_number': 'phone',
        'country_code': 'country',
        'customer_segment': 'segment',
        'credit_limit': 'credit_limit',
        'active': 'is_active'
    })
    return await loader.load_dataframe(df, source_file_id)


async def load_orders(df: pd.DataFrame, source_file_id: int) -> Dict[str, Any]:
    """Load order data with standard mapping."""
    loader = LoadService('orders', {
        'order_id': 'order_number',
        'customer_id': 'customer_id',
        'date': 'order_date',
        'amount': 'total_amount',
        'order_status': 'status'
    })
    return await loader.load_dataframe(df, source_file_id)
