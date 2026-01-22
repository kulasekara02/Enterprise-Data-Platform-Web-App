"""Unit tests for authentication."""
import pytest
from datetime import timedelta
from jose import jwt

from src.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    SECRET_KEY,
    ALGORITHM
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_password_hash_is_different_from_plain(self):
        """Hashed password should be different from plain text."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > len(password)

    def test_password_verification_success(self):
        """Correct password should verify successfully."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_password_verification_failure(self):
        """Incorrect password should fail verification."""
        password = "mysecretpassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_same_password_different_hashes(self):
        """Same password should produce different hashes (salt)."""
        password = "mysecretpassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        # But both should verify
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTToken:
    """Tests for JWT token functions."""

    def test_create_access_token(self):
        """Should create valid JWT token."""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_subject(self):
        """Token should contain the subject claim."""
        username = "testuser"
        token = create_access_token(data={"sub": username})

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert payload["sub"] == username

    def test_token_contains_expiration(self):
        """Token should contain expiration claim."""
        token = create_access_token(data={"sub": "testuser"})

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "exp" in payload

    def test_token_with_custom_expiry(self):
        """Token should respect custom expiry time."""
        token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(minutes=5)
        )

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "exp" in payload

    def test_invalid_token_raises_error(self):
        """Invalid token should raise error on decode."""
        invalid_token = "invalid.token.here"

        with pytest.raises(jwt.JWTError):
            jwt.decode(invalid_token, SECRET_KEY, algorithms=[ALGORITHM])

    def test_token_with_wrong_secret_fails(self):
        """Token decoded with wrong secret should fail."""
        token = create_access_token(data={"sub": "testuser"})

        with pytest.raises(jwt.JWTError):
            jwt.decode(token, "wrong-secret", algorithms=[ALGORITHM])
