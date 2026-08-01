"""
app/api/deps.py

Shared API dependencies:
- rate limiting
- JWT authentication for browser users
- X-API-Key fallback for trusted service-to-service calls
"""

from __future__ import annotations

import hmac

import jwt
from fastapi import Header, HTTPException, status
from jwt import InvalidTokenError
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _validate_jwt(token: str) -> None:
    if not settings.jwt_secret_key:
        raise _unauthorized()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        raise _unauthorized() from exc

    if payload.get("type") != "access" or not payload.get("sub"):
        raise _unauthorized()


async def require_api_key(
    authorization: str = Header(default=""),
    x_api_key: str = Header(default=""),
) -> None:
    """
    Protect API routes.

    Browser UI:
        Authorization: Bearer <JWT>

    Internal/service clients:
        X-API-Key: <API key>

    Existing protected routes can keep using Depends(require_api_key).
    """

    if x_api_key and hmac.compare_digest(x_api_key, settings.api_key):
        return

    if authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token:
            _validate_jwt(token)
            return

    raise _unauthorized()
