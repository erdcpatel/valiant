"""
Environment configuration and preset profile management.
Allows configuring allowed environments (DEV / UAT / PROD) and isolating
database storage per environment.
"""
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class EnvironmentInfo(BaseModel):
    id: str
    label: str
    badge: str
    color: str  # e.g., "emerald", "amber", "rose", "sky", "indigo"
    description: str
    is_prod: bool = False
    requires_confirmation: bool = False


DEFAULT_ENV_DEFINITIONS: Dict[str, EnvironmentInfo] = {
    "dev": EnvironmentInfo(
        id="dev",
        label="Development",
        badge="DEV",
        color="emerald",
        description="Local sandbox and feature development",
        is_prod=False,
        requires_confirmation=False,
    ),
    "uat": EnvironmentInfo(
        id="uat",
        label="UAT / Staging",
        badge="UAT",
        color="amber",
        description="Pre-production integration and user acceptance testing",
        is_prod=False,
        requires_confirmation=False,
    ),
    "prod": EnvironmentInfo(
        id="prod",
        label="Production",
        badge="PROD",
        color="rose",
        description="Live customer-facing environment with strict audit controls",
        is_prod=True,
        requires_confirmation=True,
    ),
}


def get_allowed_environment_ids() -> List[str]:
    """Retrieve list of enabled environment IDs (default: dev, uat, prod)."""
    env_str = os.getenv("VALIANT_ALLOWED_ENVS", "dev,uat,prod")
    allowed = [e.strip().lower() for e in env_str.split(",") if e.strip()]
    return allowed if allowed else ["dev"]


def get_allowed_environments() -> List[EnvironmentInfo]:
    """Retrieve structured metadata for all allowed environments."""
    allowed_ids = get_allowed_environment_ids()
    result = []
    for env_id in allowed_ids:
        if env_id in DEFAULT_ENV_DEFINITIONS:
            result.append(DEFAULT_ENV_DEFINITIONS[env_id])
        else:
            is_prod = "prod" in env_id
            result.append(
                EnvironmentInfo(
                    id=env_id,
                    label=env_id.upper(),
                    badge=env_id.upper()[:4],
                    color="rose" if is_prod else "indigo",
                    description=f"Custom environment: {env_id}",
                    is_prod=is_prod,
                    requires_confirmation=is_prod,
                )
            )
    return result


def get_default_environment() -> str:
    """Return default active environment."""
    allowed = get_allowed_environment_ids()
    return allowed[0] if allowed else "dev"


def normalize_environment(env: Optional[str]) -> str:
    """Normalize input environment or fall back to default."""
    if not env:
        return get_default_environment()
    env = str(env).strip().lower()
    allowed = get_allowed_environment_ids()
    if env in allowed or env == "test":
        return env
    return get_default_environment()
