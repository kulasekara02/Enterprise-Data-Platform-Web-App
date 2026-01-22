"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from src.core.security import (
    hash_password, verify_password, create_access_token, get_current_user, TokenData
)
from src.core.database import get_db_dependency

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: dict


class UserCreate(BaseModel):
    """User creation schema."""
    username: str
    email: str
    password: str
    role: str = "viewer"


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db=Depends(get_db_dependency)):
    """Authenticate user and return JWT token."""
    # Find user
    db.execute(
        "SELECT id, username, email, password_hash, role FROM users WHERE username = :1",
        [request.username]
    )
    row = db.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    user_id, username, email, password_hash, role = row

    # Verify password
    if not verify_password(request.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Create token
    token = create_access_token({
        "user_id": user_id,
        "username": username,
        "role": role
    })

    return LoginResponse(
        access_token=token,
        user={"id": user_id, "username": username, "email": email, "role": role}
    )


@router.get("/me")
async def get_current_user_info(user: TokenData = Depends(get_current_user)):
    """Get current user information."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: UserCreate, db=Depends(get_db_dependency)):
    """Register new user (admin only in production)."""
    # Check if username exists
    db.execute("SELECT id FROM users WHERE username = :1", [request.username])
    if db.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email exists
    db.execute("SELECT id FROM users WHERE email = :1", [request.email])
    if db.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # Create user
    password_hash = hash_password(request.password)
    db.execute("""
        INSERT INTO users (username, email, password_hash, role)
        VALUES (:1, :2, :3, :4)
    """, [request.username, request.email, password_hash, request.role])

    return {"message": "User created successfully"}
