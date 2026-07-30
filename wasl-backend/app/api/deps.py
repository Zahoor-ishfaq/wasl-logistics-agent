"""
app/api/deps.py

Shared API dependencies: API-key authentication and the rate limiter.

Keeping these in one place means every route enforces the same rules,
and the rules can change in exactly one file.
"""

from fastapi import Header, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# ---------------------------------------------------------------------------
# Rate limiter (slowapi)
# ---------------------------------------------------------------------------
# Keyed by client IP. In-memory storage is fine for single-instance v1;
# for multi-instance you'd point storage_uri at Redis.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)


# ---------------------------------------------------------------------------
# API key auth
# ---------------------------------------------------------------------------
async def require_api_key(x_api_key: str = Header(default="")) -> None:
    """
    FastAPI dependency that enforces the X-API-Key header.

    Attach it to a route (or router) and the route returns 401 unless
    the caller sends the correct key. The key itself lives in settings
    (from .env), never in code.

    Usage:
        @router.post("/answer", dependencies=[Depends(require_api_key)])
    """
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Send it in the X-API-Key header.",
        )
