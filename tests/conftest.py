"""Pytest configuration and fixtures."""
import os
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Set testing environment before imports
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app():
    """Create FastAPI application for testing."""
    from src.api.main import app as fastapi_app
    return fastapi_app


@pytest.fixture
def client(app) -> Generator:
    """Create synchronous test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client(app) -> AsyncGenerator:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_db():
    """Mock database connection."""
    mock = AsyncMock()
    mock.acquire = AsyncMock()
    mock.acquire.return_value.__aenter__ = AsyncMock()
    mock.acquire.return_value.__aexit__ = AsyncMock()
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis connection."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "role": "analyst",
        "is_active": True
    }


@pytest.fixture
def auth_headers(sample_user_data):
    """Generate auth headers with valid JWT token."""
    from src.core.security import create_access_token

    token = create_access_token(data={"sub": sample_user_data["username"]})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_file_data():
    """Sample file data for testing."""
    return {
        "id": 1,
        "filename": "test_file_abc123.csv",
        "original_name": "customers.csv",
        "file_type": "csv",
        "file_size": 1024,
        "row_count": 100,
        "status": "completed",
        "uploaded_by": 1,
        "uploaded_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return b"""customer_code,name,email,phone,country,segment,credit_limit
CUST001,John Doe,john@example.com,+1234567890,USA,Enterprise,50000
CUST002,Jane Smith,jane@example.com,+1987654321,UK,SMB,25000
CUST003,Bob Wilson,bob@example.com,+1122334455,Canada,Enterprise,75000
"""


@pytest.fixture
def sample_invalid_csv_content():
    """Sample invalid CSV content for testing validation."""
    return b"""customer_code,name,email,phone,country,segment,credit_limit
,Missing Name,invalid-email,phone,USA,Enterprise,50000
CUST002,,jane@example.com,+1987654321,UK,SMB,-100
CUST001,Duplicate Code,test@test.com,+1234567890,Canada,Enterprise,75000
"""


@pytest.fixture
def temp_upload_dir(tmp_path):
    """Create temporary upload directory."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return upload_dir


@pytest.fixture
def mock_celery_task():
    """Mock Celery task."""
    mock = MagicMock()
    mock.delay = MagicMock(return_value=MagicMock(id="test-task-id"))
    mock.apply_async = MagicMock(return_value=MagicMock(id="test-task-id"))
    return mock


# Markers
def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
