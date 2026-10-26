from __future__ import annotations

from typing import Any

from ..utils.id_generator import generate_id
from .common import copy_record, db, now_iso, persist


def _users() -> list[dict[str, Any]]:
    """Return the mutable users collection from the database."""
    return db()["users"]


def sanitize_user(user: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a user object without sensitive authentication fields."""
    if user is None:
        return None
    sanitized = dict(user)
    sanitized.pop("password", None)
    return sanitized


def find_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Find user by id and return it when available."""
    user = next((user for user in _users() if user["id"] == user_id), None)
    return sanitize_user(copy_record(user))


def find_user_auth_by_email(email: str) -> dict[str, Any] | None:
    """Find user auth by email and return it when available."""
    return copy_record(next((user for user in _users() if user["email"].lower() == email.lower()), None))


def get_all_users() -> list[dict[str, Any]]:
    """Return all users data for the requested context."""
    return [sanitize_user(copy_record(user)) for user in _users()]


def create_user(user_data: dict[str, Any]) -> dict[str, Any]:
    """Create user data and return the created payload."""
    user = {
        "id": user_data.get("id", generate_id()),
        "username": user_data["username"],
        "email": user_data["email"],
        "password": user_data["password"],
        "role": user_data.get("role", "user"),
        "createdAt": user_data.get("createdAt", now_iso()),
        "updatedAt": user_data.get("updatedAt", now_iso()),
    }
    _users().append(user)
    persist()
    return sanitize_user(copy_record(user))


def update_user(user_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update user and return the updated payload."""
    for user in _users():
        if user["id"] == user_id:
            user.update({key: value for key, value in updates.items() if value is not None})
            user["updatedAt"] = now_iso()
            persist()
            return sanitize_user(copy_record(user))
    return None


def delete_user(user_id: str) -> bool:
    """Delete user data for the requested context."""
    users = _users()
    index = next((i for i, user in enumerate(users) if user["id"] == user_id), None)
    if index is None:
        return False
    del users[index]
    persist()
    return True


def username_exists(username: str) -> bool:
    """Return whether a username already exists in storage."""
    return any(user["username"].lower() == username.lower() for user in _users())


def email_exists(email: str) -> bool:
    """Return whether an email address already exists in storage."""
    return any(user["email"].lower() == email.lower() for user in _users())


def search_users(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search users records using the provided filters."""
    if not query:
        return get_all_users()[:limit]
    lowered = query.lower()
    matches = [user for user in _users() if lowered in user["username"].lower()]
    return [sanitize_user(copy_record(user)) for user in matches[:limit]]


def delete_user_with_cascade(user_id: str) -> bool:
    """Delete user with cascade data for the requested context."""
    if not any(user["id"] == user_id for user in _users()):
        return False

    from .comment_model import delete_comments_by_post_id
    from .follow_model import remove_follows_by_user_id
    from .like_model import remove_likes_by_user_id
    from .moment_model import delete_moments_by_user_id
    from .post_model import delete_posts_by_user_id, get_posts_by_user_id

    posts = get_posts_by_user_id(user_id, limit=10_000, offset=0)
    delete_posts_by_user_id(user_id)
    remove_likes_by_user_id(user_id)
    remove_follows_by_user_id(user_id)
    delete_moments_by_user_id(user_id)

    for post in posts:
        delete_comments_by_post_id(post["id"])

    remaining_users = [user for user in _users() if user["id"] != user_id]
    db()["users"] = remaining_users
    persist()
    return True

