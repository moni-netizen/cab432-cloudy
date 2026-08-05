from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException, status

from ..config.constants import ROLE_MODERATOR, TOKEN_EXPIRY_HOURS
from ..config.settings import settings
from ..errors import AppError, forbidden_error, unauthorised_error
from ..models.user_model import find_user_by_id


def generate_token(user: dict) -> str:
    """Generate a signed JWT for the authenticated user."""
    payload = {
        "sub": user["id"],
        "role": user["role"],
        "username": user["username"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _decode_token(token: str) -> dict:
    """Decode and verify a JWT token payload."""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


async def authenticate(authorization: str | None = Header(default=None)) -> dict:
    """Validate a bearer token and return the authenticated user context."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = _decode_token(token)
    except Exception as exc:  # pragma: no cover - translated to 401
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    user = find_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token user")

    return {
        "userId": user["id"],
        "userRole": payload.get("role", user["role"]),
        "username": payload.get("username", user["username"]),
    }


async def optional_authenticate(authorization: str | None = Header(default=None)) -> dict | None:
    """Return authenticated user context when a valid bearer token is provided."""
    if not authorization:
        return None
    try:
        return await authenticate(authorization)
    except HTTPException:
        return None


async def require_moderator(current_user: dict = Depends(authenticate)) -> dict:
    """Require moderator role before allowing access to protected handlers."""
    if current_user.get("userRole") != ROLE_MODERATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderator access required")
    return current_user

