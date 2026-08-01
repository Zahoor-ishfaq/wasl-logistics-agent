"""
app/api/routes_auth.py

JWT login endpoint for the Wasl UI.
The existing X-API-Key authentication remains supported for internal/service use.
"""

import hmac
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import limiter
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def _create_access_token(username: str) -> str:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": username,
        "type": "access",
        "iat": now,
        "exp": expires,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, credentials: LoginRequest) -> TokenResponse:
    if not settings.jwt_secret_key or not settings.auth_password_hash:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT authentication is not configured.",
        )

    username_ok = hmac.compare_digest(
        credentials.username,
        settings.auth_username,
    )

    try:
        password_ok = bcrypt.checkpw(
            credentials.password.encode("utf-8"),
            settings.auth_password_hash.encode("utf-8"),
        )
    except ValueError:
        password_ok = False

    if not username_ok or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = _create_access_token(credentials.username)

    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_minutes * 60,
    )
