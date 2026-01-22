"""Unit tests for data validation."""
import pytest
import pandas as pd

from src.services.validate import (
    DataValidator,
    ValidationResult,
    RequiredRule,
    TypeRule,
    RangeRule,
    PatternRule,
    EmailRule,
    DateRule,
    EnumRule,
    ErrorType,
    create_customer_validator,
    create_order_validator
)


class TestRequiredRule:
    """Tests for RequiredRule validation."""

    def test_required_field_present(self):
        """Should pass when required field has value."""
        rule = RequiredRule("name")
        row = {"name": "John Doe"}

        result = rule.validate(row["name"], row)

        assert result is None

    def test_required_field_missing(self):
        """Should fail when required field is None."""
        rule = RequiredRule("name")
        row = {"name": None}

        result = rule.validate(row["name"], row)

        assert result is not None
        assert "required" in result.lower()

    def test_required_field_empty_string(self):
        """Should fail when required field is empty string."""
        rule = RequiredRule("name")
        row = {"name": "   "}

        result = rule.validate(row["name"], row)

        assert result is not None

    def test_required_field_nan(self):
        """Should fail when required field is NaN."""
        rule = RequiredRule("name")
        row = {"name": pd.NA}

        result = rule.validate(row["name"], row)

        assert result is not None


class TestTypeRule:
    """Tests for TypeRule validation."""

    def test_integer_valid(self):
        """Should pass for valid integer."""
        rule = TypeRule("age", int)
        row = {"age": "25"}

        result = rule.validate(row["age"], row)

        assert result is None

    def test_integer_invalid(self):
        """Should fail for non-integer string."""
        rule = TypeRule("age", int)
        row = {"age": "twenty-five"}

        result = rule.validate(row["age"], row)

        assert result is not None

    def test_float_valid(self):
        """Should pass for valid float."""
        rule = TypeRule("price", float)
        row = {"price": "19.99"}

        result = rule.validate(row["price"], row)

        assert result is None

    def test_none_value_passes(self):
        """None values should pass (let RequiredRule handle)."""
        rule = TypeRule("age", int)
        row = {"age": None}

        result = rule.validate(row["age"], row)

        assert result is None


class TestRangeRule:
    """Tests for RangeRule validation."""

    def test_value_in_range(self):
        """Should pass when value is within range."""
        rule = RangeRule("amount", min_val=0, max_val=100)
        row = {"amount": 50}

        result = rule.validate(row["amount"], row)

        assert result is None

    def test_value_below_min(self):
        """Should fail when value is below minimum."""
        rule = RangeRule("amount", min_val=0)
        row = {"amount": -10}

        result = rule.validate(row["amount"], row)

        assert result is not None
        assert "at least" in result.lower()

    def test_value_above_max(self):
        """Should fail when value is above maximum."""
        rule = RangeRule("amount", max_val=100)
        row = {"amount": 150}

        result = rule.validate(row["amount"], row)

        assert result is not None
        assert "at most" in result.lower()

    def test_boundary_values_pass(self):
        """Boundary values should pass."""
        rule = RangeRule("amount", min_val=0, max_val=100)

        assert rule.validate(0, {}) is None
        assert rule.validate(100, {}) is None


class TestEmailRule:
    """Tests for EmailRule validation."""

    @pytest.mark.parametrize("email", [
        "test@example.com",
        "user.name@domain.org",
        "user+tag@example.co.uk",
        "user123@test.io"
    ])
    def test_valid_emails(self, email):
        """Should pass for valid email formats."""
        rule = EmailRule("email")
        row = {"email": email}

        result = rule.validate(row["email"], row)

        assert result is None

    @pytest.mark.parametrize("email", [
        "invalid",
        "no@domain",
        "@nodomain.com",
        "spaces in@email.com",
        "missing@.com"
    ])
    def test_invalid_emails(self, email):
        """Should fail for invalid email formats."""
        rule = EmailRule("email")
        row = {"email": email}

        result = rule.validate(row["email"], row)

        assert result is not None


class TestDateRule:
    """Tests for DateRule validation."""

    def test_valid_date_default_format(self):
        """Should pass for valid date in default format."""
        rule = DateRule("date")
        row = {"date": "2024-01-15"}

        result = rule.validate(row["date"], row)

        assert result is None

    def test_invalid_date_format(self):
        """Should fail for invalid date format."""
        rule = DateRule("date")
        row = {"date": "15/01/2024"}

        result = rule.validate(row["date"], row)

        assert result is not None

    def test_custom_date_format(self):
        """Should validate against custom format."""
        rule = DateRule("date", date_format="%d/%m/%Y")
        row = {"date": "15/01/2024"}

        result = rule.validate(row["date"], row)

        assert result is None


class TestEnumRule:
    """Tests for EnumRule validation."""

    def test_value_in_enum(self):
        """Should pass when value is in allowed set."""
        rule = EnumRule("status", ["active", "inactive", "pending"])
        row = {"status": "active"}

        result = rule.validate(row["status"], row)

        assert result is None

    def test_value_not_in_enum(self):
        """Should fail when value is not in allowed set."""
        rule = EnumRule("status", ["active", "inactive"])
        row = {"status": "unknown"}

        result = rule.validate(row["status"], row)

        assert result is not None
        assert "must be one of" in result.lower()


class TestDataValidator:
    """Tests for DataValidator class."""

    def test_validate_row_no_rules(self):
        """Should pass with no rules."""
        validator = DataValidator()
        row = {"name": "John", "age": 30}

        errors = validator.validate_row(row, 1)

        assert len(errors) == 0

    def test_validate_row_with_errors(self):
        """Should return errors for invalid data."""
        validator = DataValidator()
        validator.add_rule(RequiredRule("name"))
        validator.add_rule(RangeRule("age", min_val=0, max_val=150))

        row = {"name": None, "age": 200}

        errors = validator.validate_row(row, 1)

        assert len(errors) == 2

    def test_unique_check(self):
        """Should detect duplicate values."""
        validator = DataValidator()
        validator.add_unique_check("id")

        errors1 = validator.validate_row({"id": "001"}, 1)
        errors2 = validator.validate_row({"id": "002"}, 2)
        errors3 = validator.validate_row({"id": "001"}, 3)  # Duplicate

        assert len(errors1) == 0
        assert len(errors2) == 0
        assert len(errors3) == 1
        assert errors3[0].error_type == ErrorType.DUPLICATE

    def test_validate_dataframe(self):
        """Should validate entire DataFrame."""
        validator = DataValidator()
        validator.add_rule(RequiredRule("name"))
        validator.add_rule(EmailRule("email"))

        df = pd.DataFrame([
            {"name": "John", "email": "john@test.com"},
            {"name": "", "email": "invalid"},
            {"name": "Jane", "email": "jane@test.com"}
        ])

        result = validator.validate_dataframe(df)

        assert isinstance(result, ValidationResult)
        assert result.total_rows == 3
        assert result.error_rows == 1
        assert result.valid_rows == 2

    def test_chain_rules(self):
        """Should support method chaining."""
        validator = (DataValidator()
            .add_rule(RequiredRule("name"))
            .add_rule(EmailRule("email"))
            .add_unique_check("id"))

        assert len(validator.rules) == 2
        assert len(validator.unique_fields) == 1


class TestPrebuiltValidators:
    """Tests for pre-built validator factories."""

    def test_customer_validator(self):
        """Customer validator should validate customer data."""
        validator = create_customer_validator()

        valid_row = {
            "customer_code": "CUST001",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "credit_limit": 50000
        }

        errors = validator.validate_row(valid_row, 1)

        assert len(errors) == 0

    def test_order_validator(self):
        """Order validator should validate order data."""
        validator = create_order_validator()

        valid_row = {
            "order_number": "ORD001",
            "customer_id": 1,
            "order_date": "2024-01-15",
            "total_amount": 99.99,
            "status": "pending"
        }

        errors = validator.validate_row(valid_row, 1)

        assert len(errors) == 0
