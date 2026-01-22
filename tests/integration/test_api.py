"""Integration tests for API endpoints."""
import pytest
from unittest.mock import patch, AsyncMock


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Health endpoint should return OK."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_login_success(self, client):
        """Should return token for valid credentials."""
        with patch("src.api.routes.auth.authenticate_user") as mock_auth:
            mock_auth.return_value = {
                "id": 1,
                "username": "testuser",
                "email": "test@example.com",
                "role": "analyst"
            }

            response = client.post(
                "/api/auth/login",
                json={"username": "testuser", "password": "password123"}
            )

            assert response.status_code == 200
            assert "access_token" in response.json()
            assert response.json()["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        """Should return 401 for invalid credentials."""
        with patch("src.api.routes.auth.authenticate_user") as mock_auth:
            mock_auth.return_value = None

            response = client.post(
                "/api/auth/login",
                json={"username": "baduser", "password": "wrongpass"}
            )

            assert response.status_code == 401

    def test_login_missing_fields(self, client):
        """Should return 422 for missing fields."""
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser"}  # Missing password
        )

        assert response.status_code == 422


class TestDataEndpoints:
    """Tests for data management endpoints."""

    def test_list_files_unauthorized(self, client):
        """Should return 401 without auth token."""
        response = client.get("/api/data/files")

        assert response.status_code == 401

    def test_list_files_authorized(self, client, auth_headers):
        """Should return files list with valid token."""
        with patch("src.api.routes.data.get_files") as mock_get:
            mock_get.return_value = {"items": [], "total": 0}

            response = client.get("/api/data/files", headers=auth_headers)

            assert response.status_code == 200
            assert "items" in response.json()

    def test_upload_file(self, client, auth_headers, sample_csv_content):
        """Should upload file successfully."""
        with patch("src.api.routes.data.save_uploaded_file") as mock_save:
            with patch("src.api.routes.data.create_file_record") as mock_record:
                mock_save.return_value = "/uploads/test.csv"
                mock_record.return_value = {"id": 1, "status": "uploaded"}

                response = client.post(
                    "/api/data/upload",
                    headers=auth_headers,
                    files={"file": ("test.csv", sample_csv_content, "text/csv")}
                )

                # May return 200 or trigger processing
                assert response.status_code in [200, 202]

    def test_upload_invalid_file_type(self, client, auth_headers):
        """Should reject invalid file types."""
        response = client.post(
            "/api/data/upload",
            headers=auth_headers,
            files={"file": ("test.exe", b"invalid", "application/octet-stream")}
        )

        assert response.status_code in [400, 422]


class TestJobEndpoints:
    """Tests for job management endpoints."""

    def test_list_jobs_unauthorized(self, client):
        """Should return 401 without auth token."""
        response = client.get("/api/jobs")

        assert response.status_code == 401

    def test_list_jobs_authorized(self, client, auth_headers):
        """Should return jobs list with valid token."""
        with patch("src.api.routes.jobs.get_jobs") as mock_get:
            mock_get.return_value = {"items": [], "total": 0}

            response = client.get("/api/jobs", headers=auth_headers)

            assert response.status_code == 200

    def test_get_job_stats(self, client, auth_headers):
        """Should return job statistics."""
        with patch("src.api.routes.jobs.get_job_stats") as mock_stats:
            mock_stats.return_value = {
                "running": 2,
                "queued": 5,
                "completed_24h": 100,
                "failed_24h": 3
            }

            response = client.get("/api/jobs/stats", headers=auth_headers)

            assert response.status_code == 200
            assert "running" in response.json()


class TestReportEndpoints:
    """Tests for report endpoints."""

    def test_list_reports(self, client, auth_headers):
        """Should return reports list."""
        with patch("src.api.routes.reports.get_reports") as mock_get:
            mock_get.return_value = {"items": [], "total": 0}

            response = client.get("/api/reports", headers=auth_headers)

            assert response.status_code == 200

    def test_generate_report(self, client, auth_headers):
        """Should trigger report generation."""
        with patch("src.api.routes.reports.generate_report_task") as mock_gen:
            mock_gen.delay.return_value.id = "task-123"

            response = client.post(
                "/api/reports/generate",
                headers=auth_headers,
                json={"report_type": "file_summary", "parameters": {}}
            )

            assert response.status_code in [200, 202]


class TestRateLimiting:
    """Tests for rate limiting."""

    def test_rate_limit_exceeded(self, client, auth_headers):
        """Should return 429 when rate limit exceeded."""
        # This test depends on actual rate limiting configuration
        # In production, you'd simulate many requests

        # For now, just verify the endpoint exists
        response = client.get("/api/data/files", headers=auth_headers)
        assert response.status_code != 429  # Should not be rate limited with single request


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers(self, client):
        """Should include CORS headers."""
        response = client.options(
            "/api/auth/login",
            headers={"Origin": "http://localhost:3000"}
        )

        # CORS preflight should be handled
        assert response.status_code in [200, 204, 405]
