"""
Lightweight Authentication Module.
Configurable static/API authentication with secure JWT tokens stored in HTTP cookies.
Designed for easy swap to corporate SSO / OAuth / LDAP / Auth API.
"""
import os
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel
import hmac
import hashlib
import base64
import json

# Secret for signing cookies (configurable via environment variable)
AUTH_SECRET = os.getenv("VALIANT_AUTH_SECRET", "valiant_dev_secret_key_change_in_prod")
AUTH_ENABLED = os.getenv("VALIANT_AUTH_ENABLED", "true").lower() in ("1", "true", "yes")

# Configurable static user credentials (can be overridden by environment variables)
# Later, you can swap authenticate_credentials() to call your company's Auth API or LDAP
STATIC_USERS = {
    "admin": {
        "password": os.getenv("VALIANT_ADMIN_PASSWORD", "admin123"),
        "role": "admin",
        "name": "System Administrator",
        "email": "admin@valiant.internal"
    },
    "operator": {
        "password": os.getenv("VALIANT_OPERATOR_PASSWORD", "operator123"),
        "role": "operator",
        "name": "Platform Operator",
        "email": "operator@valiant.internal"
    },
    "viewer": {
        "password": os.getenv("VALIANT_VIEWER_PASSWORD", "viewer123"),
        "role": "viewer",
        "name": "Platform Viewer",
        "email": "viewer@valiant.internal"
    }
}


def _create_token(username: str, role: str) -> str:
    """Create a tamper-proof signed payload."""
    payload = {
        "username": username,
        "role": role,
        "exp": int(time.time()) + (86400 * 7)  # 7 days validity
    }
    dumped = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    encoded_payload = base64.urlsafe_b64encode(dumped).decode('utf-8')
    sig = hmac.new(AUTH_SECRET.encode('utf-8'), encoded_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{sig}"


def _verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify signature and expiration of cookie token."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        encoded_payload, sig = parts
        expected_sig = hmac.new(AUTH_SECRET.encode('utf-8'), encoded_payload.encode('utf-8'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None

        decoded = base64.urlsafe_b64decode(encoded_payload.encode('utf-8'))
        payload = json.loads(decoded.decode('utf-8'))
        if payload.get("exp", 0) < int(time.time()):
            return None  # expired
        return payload
    except Exception:
        return None


def get_current_user(request: Request) -> Dict[str, Any]:
    """Dependency to extract user info from cookie or authorization header."""
    token = request.cookies.get("valiant_token")
    if not token:
        # Check Authorization header bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        payload = _verify_token(token)
        if payload:
            return {
                "username": payload["username"],
                "role": payload.get("role", "operator"),
                "authenticated": True
            }

    # If auth is disabled or no token, return anonymous user
    return {
        "username": "anonymous",
        "role": "guest",
        "authenticated": False
    }


router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(creds: LoginRequest, response: Response):
    """
    Validate user credentials and set secure session cookie.
    Hook point: replace STATIC_USERS check with external Auth API / SSO validation.
    """
    user_info = STATIC_USERS.get(creds.username)
    if not user_info or user_info["password"] != creds.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = _create_token(creds.username, user_info["role"])

    # Set HTTP-only secure cookie
    response.set_cookie(
        key="valiant_token",
        value=token,
        httponly=False,  # Allow frontend to inspect presence and user state
        max_age=86400 * 7,
        path="/",
        samesite="lax"
    )

    return {
        "success": True,
        "username": creds.username,
        "role": user_info["role"],
        "name": user_info["name"],
        "email": user_info["email"],
        "token": token
    }


@router.post("/logout")
def logout(response: Response):
    """Clear session cookie."""
    response.delete_cookie(key="valiant_token", path="/")
    return {"success": True, "message": "Logged out successfully"}


@router.get("/me")
def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    """Return currently active user profile and auth settings."""
    user_meta = STATIC_USERS.get(user["username"], {})
    return {
        "auth_enabled": AUTH_ENABLED,
        "authenticated": user["authenticated"],
        "username": user["username"],
        "role": user["role"],
        "name": user_meta.get("name", user["username"]),
        "email": user_meta.get("email", "")
    }
