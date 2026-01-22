"""Unit tests for file ingestion service."""
import pytest
import pandas as pd
from pathlib import Path
from io import BytesIO

from src.services.ingest import IngestService, detect_delimiter, detect_encoding


class TestIngestService:
    """Tests for IngestService class."""

    @pytest.fixture
    def csv_file(self, tmp_path):
        """Create temporary CSV file."""
        content = """name,email,age
John,john@test.com,30
Jane,jane@test.com,25
Bob,bob@test.com,35
"""
        file_path = tmp_path / "test.csv"
        file_path.write_text(content)
        return str(file_path)

    @pytest.fixture
    def json_file(self, tmp_path):
        """Create temporary JSON file."""
        content = '[{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]'
        file_path = tmp_path / "test.json"
        file_path.write_text(content)
        return str(file_path)

    def test_init_valid_type(self, csv_file):
        """Should initialize with valid file type."""
        service = IngestService(csv_file, "csv")

        assert service.file_type == "csv"
        assert service.file_path == Path(csv_file)

    def test_init_invalid_type(self, csv_file):
        """Should raise error for invalid file type."""
        with pytest.raises(ValueError) as exc_info:
            IngestService(csv_file, "txt")

        assert "Unsupported file type" in str(exc_info.value)

    def test_get_row_count_csv(self, csv_file):
        """Should count rows in CSV file."""
        service = IngestService(csv_file, "csv")

        count = service.get_row_count()

        assert count == 3  # Excluding header

    def test_get_row_count_json(self, json_file):
        """Should count rows in JSON file."""
        service = IngestService(json_file, "json")

        count = service.get_row_count()

        assert count == 2

    def test_get_headers_csv(self, csv_file):
        """Should extract headers from CSV file."""
        service = IngestService(csv_file, "csv")

        headers = service.get_headers()

        assert headers == ["name", "email", "age"]

    def test_get_headers_json(self, json_file):
        """Should extract headers from JSON file."""
        service = IngestService(json_file, "json")

        headers = service.get_headers()

        assert "name" in headers
        assert "age" in headers

    def test_read_all_csv(self, csv_file):
        """Should read entire CSV into DataFrame."""
        service = IngestService(csv_file, "csv")

        df = service.read_all()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["name", "email", "age"]

    def test_read_all_json(self, json_file):
        """Should read entire JSON into DataFrame."""
        service = IngestService(json_file, "json")

        df = service.read_all()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_read_in_batches_csv(self, csv_file):
        """Should read CSV in batches."""
        service = IngestService(csv_file, "csv")

        batches = list(service.read_in_batches(batch_size=2))

        assert len(batches) == 2  # 3 rows / 2 batch size = 2 batches
        assert len(batches[0]) == 2
        assert len(batches[1]) == 1

    def test_preview(self, csv_file):
        """Should return preview of data."""
        service = IngestService(csv_file, "csv")

        preview = service.preview(rows=2)

        assert len(preview) == 2
        assert preview[0]["name"] == "John"

    def test_preview_limit(self, csv_file):
        """Preview should respect row limit."""
        service = IngestService(csv_file, "csv")

        preview = service.preview(rows=1)

        assert len(preview) == 1


class TestDetectDelimiter:
    """Tests for delimiter detection."""

    def test_detect_comma(self):
        """Should detect comma delimiter."""
        content = b"a,b,c\n1,2,3\n4,5,6"

        delimiter = detect_delimiter(content)

        assert delimiter == ","

    def test_detect_semicolon(self):
        """Should detect semicolon delimiter."""
        content = b"a;b;c\n1;2;3\n4;5;6"

        delimiter = detect_delimiter(content)

        assert delimiter == ";"

    def test_detect_tab(self):
        """Should detect tab delimiter."""
        content = b"a\tb\tc\n1\t2\t3\n4\t5\t6"

        delimiter = detect_delimiter(content)

        assert delimiter == "\t"

    def test_detect_pipe(self):
        """Should detect pipe delimiter."""
        content = b"a|b|c\n1|2|3\n4|5|6"

        delimiter = detect_delimiter(content)

        assert delimiter == "|"


class TestDetectEncoding:
    """Tests for encoding detection."""

    def test_detect_utf8(self, tmp_path):
        """Should detect UTF-8 encoding."""
        file_path = tmp_path / "utf8.csv"
        file_path.write_text("name,city\nJohn,München", encoding="utf-8")

        encoding = detect_encoding(str(file_path))

        assert encoding.lower() in ["utf-8", "ascii"]

    def test_detect_with_bom(self, tmp_path):
        """Should handle UTF-8 BOM."""
        file_path = tmp_path / "bom.csv"
        with open(file_path, "wb") as f:
            f.write(b'\xef\xbb\xbf')  # UTF-8 BOM
            f.write("name,value\ntest,123".encode("utf-8"))

        encoding = detect_encoding(str(file_path))

        assert encoding is not None
