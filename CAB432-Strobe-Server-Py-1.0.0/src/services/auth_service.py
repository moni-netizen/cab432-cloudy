from __future__ import annotations

import shutil
from pathlib import Path

from ..config.settings import settings
from ..config.constants import ROLE_USER
from ..errors import conflict_error, forbidden_error, not_found_error, unauthorised_error, validation_error
from ..middleware.auth import generate_token
from ..models.user_model import (
    create_user,
    delete_user_with_cascade,
    email_exists,
    find_user_auth_by_email,
    find_user_by_id,
    get_all_users,
    search_users,
)
from ..utils.enrichment import enrich_user, enrich_users
from ..utils.password import compare_password, hash_password
from ..utils.validation import validate_email, validate_password, validate_role


def register_user(user_data: dict) -> dict:
    """Register a new user account and return safe user plus JWT token."""
    email = user_data.get("email")
    password = user_data.get("password")
    requested_role = user_data.get("role", ROLE_USER)
    
    # Username is always set to match email
    username = email

    for validator in (validate_email(email), validate_password(password)):
        if not validator["valid"]:
            raise validation_error(str(validator["error"]))

    role_validation = validate_role(requested_role)
    if not role_validation["valid"]:
        raise validation_error(str(role_validation["error"]))

    if email_exists(email):
        raise conflict_error("Email already exists")

    user = create_user(
        {
            "username": username,
            "email": email,
            "password": hash_password(password),
            "role": requested_role,
        }
    )
    token = generate_token({"id": user["id"], "role": user["role"], "username": user["username"]})
    return {"user": user, "token": token}


def login_user(credentials: dict) -> dict:
    """Authenticate a user by email/password and return safe user plus JWT token."""
    email = credentials.get("email")
    password = credentials.get("password")

    if not email or not password:
        raise unauthorised_error("Invalid email or password")

    auth_user = find_user_auth_by_email(email)
    if not auth_user or not compare_password(password, auth_user["password"]):
        raise unauthorised_error("Invalid email or password")

    user = find_user_by_id(auth_user["id"])
    token = generate_token({"id": user["id"], "role": user["role"], "username": user["username"]})
    return {"user": user, "token": token}


def get_user_profile(user_id: str, current_user_id: str | None = None) -> dict:
    """Return one enriched user profile by ID."""
    user = find_user_by_id(user_id)
    if not user:
        raise not_found_error("User not found")
    return enrich_user(user, current_user_id)


def list_users(query: str = "", limit: int = 20, current_user_id: str | None = None) -> list[dict]:
    """Return enriched user list with optional query filtering and bounded limit."""
    limit = max(1, min(int(limit), 100))
    users = search_users(query or "", limit=limit) if query else get_all_users()[:limit]
    return enrich_users(users, current_user_id)


def delete_user_account(authenticated_user_id: str, target_user_id: str) -> None:
    """Delete an account owned by the authenticated user and cleanup uploads."""
    if authenticated_user_id != target_user_id:
        raise forbidden_error("You can only delete your own account")
    if not delete_user_with_cascade(target_user_id):
        raise not_found_error("User not found")

    user_uploads_dir = Path(settings.uploads_dir) / target_user_id
    if user_uploads_dir.exists():
        shutil.rmtree(user_uploads_dir, ignore_errors=True)

