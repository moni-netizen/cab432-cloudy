from __future__ import annotations

from typing import Any

from ..utils.id_generator import generate_id
from .common import copy_record, db, now_iso, persist


def _likes() -> list[dict[str, Any]]:
    """Return the mutable likes collection from the database."""
    return db()["likes"]


def find_like(post_id: str, user_id: str) -> dict[str, Any] | None:
    """Find like and return it when available."""
    return copy_record(next((like for like in _likes() if like["postId"] == post_id and like["userId"] == user_id), None))


def has_user_liked_post(post_id: str, user_id: str | None) -> bool:
    """Return whether user liked post exists for the current context."""
    if not user_id:
        return False
    return any(like["postId"] == post_id and like["userId"] == user_id for like in _likes())


def get_like_count_by_post_id(post_id: str) -> int:
    """Return like count by post id data for the requested context."""
    return sum(1 for like in _likes() if like["postId"] == post_id)


def create_like(like_data: dict[str, Any]) -> dict[str, Any]:
    """Create like data and return the created payload."""
    like = {
        "id": like_data.get("id", generate_id()),
        "postId": like_data["postId"],
        "userId": like_data["userId"],
        "createdAt": like_data.get("createdAt", now_iso()),
    }
    _likes().append(like)
    persist()
    return copy_record(like)


def remove_like(post_id: str, user_id: str) -> bool:
    """Remove like data for the requested context."""
    likes = _likes()
    index = next((i for i, like in enumerate(likes) if like["postId"] == post_id and like["userId"] == user_id), None)
    if index is None:
        return False
    del likes[index]
    persist()
    return True


def remove_likes_by_post_id(post_id: str) -> None:
    """Remove likes by post id data for the requested context."""
    db()["likes"] = [like for like in _likes() if like["postId"] != post_id]
    persist()


def remove_likes_by_user_id(user_id: str) -> None:
    """Remove likes by user id data for the requested context."""
    db()["likes"] = [like for like in _likes() if like["userId"] != user_id]
    persist()

