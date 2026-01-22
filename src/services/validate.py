"""Data validation service - validates data against rules."""
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd


class ErrorType(str, Enum):
    """Types of validation errors."""
    REQUIRED = "required"
    FORMAT = "format"
    RANGE = "range"
    DUPLICATE = "duplicate"
    TYPE = "type"
    REFERENCE = "reference"
    CUSTOM = "custom"


@dataclass
class ValidationError:
    """Represents a single validation error."""
    row_number: int
    field_name: str
    field_value: Any
    error_type: ErrorType
    error_message: str
    raw_data: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validating a dataset."""
    total_rows: int
    valid_rows: int
    error_rows: int
    errors: List[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.error_rows == 0

    @property
    def error_rate(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return self.error_rows / self.total_rows * 100


class ValidationRule:
    """Base class for validation rules."""

    def __init__(self, field: str, error_message: str = None):
        self.field = field
        self.error_message = error_message

    def validate(self, value: Any, row: Dict[str, Any]) -> Optional[str]:
        """Validate value. Return error message if invalid, None if valid."""
        raise NotImplementedError


class RequiredRule(ValidationRule):
    """Validate that field is not empty."""

    def validate(self, value: Any, row: Dict[str, Any]) -> Optional[str]:
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return self.error_message or f"{self.field} is required"
        if pd.isna(value):
            return self.error_message or f"{self.field} is required"
        return None


class TypeRule(ValidationRule):
    """Validate field type."""

    def __init__(self, field: str, expected_type: type, error_message: str = None):
        super().__init__(field, error_message)
        self.expected_type = expected_type

    def validate(self, value: Any, row: Dict[str, Any]) -> Optional[str]:
        if value is None or pd.isna(value):
            return None  # Let RequiredRule handle empty values

        if self.expected_type == int:
            try:
                int(value)
                return None
            except (ValueError, TypeError):
                return self.error_message or f"{self.field} must be an integer"

        elif self.expected_type == float:
            try:
                float(value)
                return None
            except (ValueError, TypeError):
                return self.error_message or f"{self.field} must be a number"

        elif self.expected_type == bool:
            if isinstance(value, bool):
                return None
            if str(value).lower() in ('true', 'false', '1', '0', 'yes', 'no'):
                return None
            return self.error_message or f"{self.field} must be a boolean"

        return None


class RangeRule(ValidationRule):
    """Validate numeric range."""

    def __init__(self, field: str, min_val: float = None, max_val: float = None,
                 error_message: str = None):
        super().__init__(field, error_message)
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, value: Any, row: Dict[str, Any]) -> Optional[str]:
        if value is None or pd.isna(value):
            return None

        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return f"{self.field} must be numeric for range validation"

        if self.min_val is not None and num_value < self.min_val:
            return self.error_message or f"{self.field} must be at least {self.min_val}"

        if self.max_val is not None and num_value > self.max_val:
            return self.error_message or f"{self.field} must be at most {self.max_val}"

        return None


class PatternRule(ValidationRule):
    """Validate against regex pattern."""

    def __init__(self, field: str, pattern: str, error_message: str = None):
        super().__init__(field, error_message)
        self.pattern = re.compile(pattern)

    def validate(self, value: Any, row: Dict[str, Any]) -> Optional[str]:
        if value is None or pd.isna(value):
            return None

        if not self.pattern.match(str(value)):
            return self.error_message or f"{self.field} does not match expected pattern"

        return None


class EmailRule(PatternRule):
    """Validate email format."""

    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    def __init__(self, field: str, error_message: str = None):
        super().__init__(field, self.EMAIL_PATTERN,
                        error_message or f"{field} must be a valid email address")


class DateRule(ValidationRule):
    """Validate date format."""

    def __init__(self, field: str, date_format: str = "%Y-%m-%d", error_message: str = None):
        super().__init__(field, error_message)
        self.date_format = date_format

    def validate(self, value: Any, row: Dict[str, Any]) -> Optional[str]:
        if value is None or pd.isna(value):
            return None

        try:
            if isinstance(value, (datetime, pd.Timestamp)):
                return None
            datetime.strptime(str(value), self.date_format)
            return None
        except ValueError:
            return self.error_message or f"{self.field} must be a valid date ({self.date_format})"


class EnumRule(ValidationRule):
    """Validate value is in allowed set."""

    def __init__(self, field: str, allowed_values: List[Any], error_message: str = None):
        super().__init__(field, error_message)
        self.allowed_values = set(allowed_values)

    def validate(self, value: Any, row: Dict[str, Any]) -> Optional[str]:
        if value is None or pd.isna(value):
            return None

        if value not in self.allowed_values:
            return self.error_message or f"{self.field} must be one of: {', '.join(map(str, self.allowed_values))}"

        return None


class CustomRule(ValidationRule):
    """Custom validation using a callable."""

    def __init__(self, field: str, validator: Callable[[Any, Dict], bool],
                 error_message: str = None):
        super().__init__(field, error_message)
        self.validator = validator

    def validate(self, value: Any, row: Dict[str, Any]) -> Optional[str]:
        if not self.validator(value, row):
            return self.error_message or f"{self.field} failed custom validation"
        return None


class DataValidator:
    """Main validator class that applies rules to data."""

    def __init__(self):
        self.rules: List[ValidationRule] = []
        self.unique_fields: List[str] = []
        self._seen_values: Dict[str, set] = {}

    def add_rule(self, rule: ValidationRule) -> 'DataValidator':
        """Add a validation rule."""
        self.rules.append(rule)
        return self

    def add_unique_check(self, field: str) -> 'DataValidator':
        """Add uniqueness check for a field."""
        self.unique_fields.append(field)
        self._seen_values[field] = set()
        return self

    def validate_row(self, row: Dict[str, Any], row_number: int) -> List[ValidationError]:
        """Validate a single row."""
        errors = []

        # Apply rules
        for rule in self.rules:
            value = row.get(rule.field)
            error_msg = rule.validate(value, row)

            if error_msg:
                error_type = self._get_error_type(rule)
                errors.append(ValidationError(
                    row_number=row_number,
                    field_name=rule.field,
                    field_value=value,
                    error_type=error_type,
                    error_message=error_msg,
                    raw_data=str(row)
                ))

        # Check uniqueness
        for field in self.unique_fields:
            value = row.get(field)
            if value is not None and not pd.isna(value):
                if value in self._seen_values[field]:
                    errors.append(ValidationError(
                        row_number=row_number,
                        field_name=field,
                        field_value=value,
                        error_type=ErrorType.DUPLICATE,
                        error_message=f"Duplicate value for {field}: {value}",
                        raw_data=str(row)
                    ))
                else:
                    self._seen_values[field].add(value)

        return errors

    def _get_error_type(self, rule: ValidationRule) -> ErrorType:
        """Determine error type from rule type."""
        if isinstance(rule, RequiredRule):
            return ErrorType.REQUIRED
        elif isinstance(rule, (PatternRule, EmailRule, DateRule)):
            return ErrorType.FORMAT
        elif isinstance(rule, RangeRule):
            return ErrorType.RANGE
        elif isinstance(rule, TypeRule):
            return ErrorType.TYPE
        elif isinstance(rule, EnumRule):
            return ErrorType.FORMAT
        else:
            return ErrorType.CUSTOM

    def validate_dataframe(self, df: pd.DataFrame, start_row: int = 1) -> ValidationResult:
        """Validate entire DataFrame."""
        all_errors = []
        error_row_numbers = set()

        for idx, row in df.iterrows():
            row_number = start_row + idx
            row_dict = row.to_dict()
            errors = self.validate_row(row_dict, row_number)

            if errors:
                error_row_numbers.add(row_number)
                all_errors.extend(errors)

        return ValidationResult(
            total_rows=len(df),
            valid_rows=len(df) - len(error_row_numbers),
            error_rows=len(error_row_numbers),
            errors=all_errors
        )

    def reset(self):
        """Reset validator state (for unique checks)."""
        for field in self.unique_fields:
            self._seen_values[field] = set()


# Pre-built validators for common data types
def create_customer_validator() -> DataValidator:
    """Create validator for customer data."""
    return (DataValidator()
        .add_rule(RequiredRule("customer_code"))
        .add_rule(RequiredRule("name"))
        .add_rule(EmailRule("email"))
        .add_rule(PatternRule("phone", r'^\+?[\d\s-]{10,20}$', "Invalid phone format"))
        .add_rule(RangeRule("credit_limit", min_val=0, max_val=10000000))
        .add_unique_check("customer_code"))


def create_order_validator() -> DataValidator:
    """Create validator for order data."""
    return (DataValidator()
        .add_rule(RequiredRule("order_number"))
        .add_rule(RequiredRule("customer_id"))
        .add_rule(RequiredRule("order_date"))
        .add_rule(DateRule("order_date"))
        .add_rule(RequiredRule("total_amount"))
        .add_rule(RangeRule("total_amount", min_val=0))
        .add_rule(EnumRule("status", ["pending", "confirmed", "shipped", "delivered", "cancelled"]))
        .add_unique_check("order_number"))
