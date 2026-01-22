"""Oracle Database connection management."""
import oracledb
from contextlib import contextmanager
from src.api.config import settings
import structlog

logger = structlog.get_logger()

# Connection pool
pool = None


async def init_db():
    """Initialize database connection pool."""
    global pool
    try:
        # Parse connection URL
        # Format: oracle+oracledb://user:pass@host:port/?service_name=XE
        url = settings.DATABASE_URL
        if url.startswith("oracle+oracledb://"):
            url = url.replace("oracle+oracledb://", "")

        # Extract parts
        user_pass, rest = url.split("@")
        user, password = user_pass.split(":")
        host_port, params = rest.split("/?")
        host, port = host_port.split(":")
        service_name = params.split("=")[1]

        dsn = f"{host}:{port}/{service_name}"

        pool = oracledb.create_pool(
            user=user,
            password=password,
            dsn=dsn,
            min=2,
            max=10,
            increment=1
        )
        logger.info("Database pool created", dsn=dsn)
    except Exception as e:
        logger.error("Failed to create database pool", error=str(e))
        raise


async def close_db():
    """Close database connection pool."""
    global pool
    if pool:
        pool.close()
        logger.info("Database pool closed")


@contextmanager
def get_db():
    """Get database connection from pool."""
    connection = pool.acquire()
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        pool.release(connection)


def get_db_dependency():
    """FastAPI dependency for database connection."""
    with get_db() as cursor:
        yield cursor
