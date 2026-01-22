"""FastAPI dependencies for dependency injection."""
from typing import Annotated, Optional
from functools import lru_cache

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from src.api.config import Settings, settings
from src.core.security import SECRET_KEY, ALGORITHM
from src.api.schemas import UserResponse

# OAuth2 scheme for JWT tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return settings


async def get_current_user_optional(
    token: Annotated[Optional[str], Depends(oauth2_scheme)]
) -> Optional[dict]:
    """
    Get current user from JWT token (optional).
    Returns None if no valid token provided.
    """
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None

        # In production, fetch full user from database
        return {
            "username": username,
            "role": payload.get("role", "viewer")
        }

    except JWTError:
        return None


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> dict:
    """
    Get current user from JWT token (required).
    Raises 401 if no valid token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        # In production, fetch full user from database
        return {
            "id": payload.get("user_id", 1),
            "username": username,
            "email": payload.get("email", f"{username}@example.com"),
            "role": payload.get("role", "viewer"),
            "is_active": True
        }

    except JWTError:
        raise credentials_exception


async def get_current_active_user(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Get current active user. Raises 400 if user is inactive."""
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_role(*allowed_roles: str):
    """
    Dependency factory for role-based access control.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: dict = Depends(require_role("admin"))):
            ...
    """
    async def role_checker(
        current_user: Annotated[dict, Depends(get_current_active_user)]
    ) -> dict:
        user_role = current_user.get("role", "viewer")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' not authorized for this action"
            )
        return current_user

    return role_checker


# Commonly used role dependencies
AdminUser = Annotated[dict, Depends(require_role("admin"))]
AnalystUser = Annotated[dict, Depends(require_role("admin", "analyst"))]
AuthenticatedUser = Annotated[dict, Depends(get_current_active_user)]


class RateLimiter:
    """
    Simple in-memory rate limiter.
    In production, use Redis-based rate limiting.
    """

    def __init__(self, requests: int = 100, period: int = 60):
        self.requests = requests
        self.period = period
        self._cache: dict = {}

    async def __call__(self, request: Request) -> None:
        # Get client identifier
        client_id = request.client.host if request.client else "unknown"

        # In production, implement proper rate limiting with Redis
        # This is a simplified placeholder

        # For now, just pass through
        pass


# Rate limiter instances
default_rate_limiter = RateLimiter(requests=100, period=60)
strict_rate_limiter = RateLimiter(requests=10, period=60)


async def get_db():
    """
    Database connection dependency.
    Yields a database connection from the pool.
    """
    from src.core.database import get_db_pool

    pool = await get_db_pool()

    async with pool.acquire() as connection:
        yield connection


async def get_redis():
    """
    Redis connection dependency.
    """
    import redis.asyncio as redis

    client = redis.from_url(settings.REDIS_URL)

    try:
        yield client
    finally:
        await client.close()


# Type aliases for cleaner annotations
DBConnection = Annotated[any, Depends(get_db)]
RedisClient = Annotated[any, Depends(get_redis)]
CurrentUser = Annotated[dict, Depends(get_current_active_user)]
OptionalUser = Annotated[Optional[dict], Depends(get_current_user_optional)]
