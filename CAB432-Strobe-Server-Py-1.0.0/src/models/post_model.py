from __future__ import annotations

from typing import Any

from ..utils.id_generator import generate_id
from .common import copy_record, db, now_iso, persist


def _posts() -> list[dict[str, Any]]:
    """Return the mutable posts collection from the database."""
    return db()["posts"]


def find_post_by_id(post_id: str) -> dict[str, Any] | None:
    """Find post by id and return it when available."""
    return copy_record(next((post for post in _posts() if post["id"] == post_id), None))


def get_posts_by_user_id(user_id: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """Return posts by user id data for the requested context."""
    posts = [copy_record(post) for post in _posts() if post["userId"] == user_id]
    posts.sort(key=lambda post: post["createdAt"], reverse=True)
    return posts[offset:offset + limit]


def get_all_posts(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """Return all posts data for the requested context."""
    posts = [copy_record(post) for post in _posts()]
    posts.sort(key=lambda post: post["createdAt"], reverse=True)
    return posts[offset:offset + limit]


def create_post(post_data: dict[str, Any]) -> dict[str, Any]:
    """Create post data and return the created payload."""
    post = {
        "id": post_data.get("id", generate_id()),
        "userId": post_data["userId"],
        "title": post_data["title"],
        "description": post_data.get("description", ""),
        "images": list(post_data.get("images", [])),
        "status": post_data.get("status", "active"),
        "hiddenBy": post_data.get("hiddenBy"),
        "hiddenAt": post_data.get("hiddenAt"),
        "createdAt": post_data.get("createdAt", now_iso()),
        "updatedAt": post_data.get("updatedAt", now_iso()),
    }
    _posts().append(post)
    persist()
    return copy_record(post)


def update_post(post_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update post and return the updated payload."""
    for post in _posts():
        if post["id"] == post_id:
            for key, value in updates.items():
                if value is not None and key != "id":
                    post[key] = value
            post["updatedAt"] = now_iso()
            persist()
            return copy_record(post)
    return None


def delete_post(post_id: str) -> bool:
    """Delete post data for the requested context."""
    posts = _posts()
    index = next((i for i, post in enumerate(posts) if post["id"] == post_id), None)
    if index is None:
        return False
    del posts[index]
    persist()
    return True


def get_posts_from_users(user_ids: list[str], limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """Return posts from users data for the requested context."""
    posts = [copy_record(post) for post in _posts() if post["userId"] in user_ids]
    posts.sort(key=lambda post: post["createdAt"], reverse=True)
    return posts[offset:offset + limit]


def get_post_count_by_user_id(user_id: str) -> int:
    """Return post count by user id data for the requested context."""
    return sum(1 for post in _posts() if post["userId"] == user_id)


def delete_posts_by_user_id(user_id: str) -> None:
    """Delete posts by user id data for the requested context."""
    db()["posts"] = [post for post in _posts() if post["userId"] != user_id]
    persist()

