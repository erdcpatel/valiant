"""API key authentication dependency for FastAPI."""
from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from valiant.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    """
    FastAPI dependency. Validates the X-API-Key header.
    Auth is skipped entirely when no keys are configured (dev mode).
    """
    if not settings.auth_enabled:
        return "dev-no-auth"

    if not api_key or api_key not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass a valid key in the X-API-Key header.",
        )
    return api_key
