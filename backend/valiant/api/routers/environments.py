"""
Environments API Router.
Exposes available environment definitions (DEV, UAT, PROD) and current configuration.
"""
from fastapi import APIRouter, Request, Query
from typing import Dict, Any, List, Optional
from ...core.environments import (
    get_allowed_environments,
    get_default_environment,
    normalize_environment,
    EnvironmentInfo
)

router = APIRouter(prefix="/environments", tags=["Environments"])


@router.get("", response_model=Dict[str, Any])
def list_environments(
    request: Request,
    active: Optional[str] = Query(None, description="Explicit active environment to query or check")
):
    """Retrieve all enabled environments and active selection."""
    header_env = request.headers.get("x-valiant-env")
    current_env = normalize_environment(active or header_env or get_default_environment())
    allowed = get_allowed_environments()

    return {
        "success": True,
        "active_env": current_env,
        "default_env": get_default_environment(),
        "allowed_environments": [e.model_dump() for e in allowed]
    }
