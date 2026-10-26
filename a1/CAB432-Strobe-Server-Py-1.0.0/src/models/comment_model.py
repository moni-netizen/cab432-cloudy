from __future__ import annotations

from typing import Any

from ..utils.id_generator import generate_id
from .common import copy_record, db, now_iso, persist


def _comments() -> list[dict[str, Any]]:
    """Return the mutable comments collection from the database."""
    return db()["comments"]


def find_comment_by_id(comment_id: str) -> dict[str, Any] | None:
    """Find comment by id and return it when available."""
    return copy_record(next((comment for comment in _comments() if comment["id"] == comment_id), None))


def get_comments_by_post_id(post_id: str) -> list[dict[str, Any]]:
    """Return comments by post id data for the requested context."""
    comments = [copy_record(comment) for comment in _comments() if comment["postId"] == post_id]
    comments.sort(key=lambda comment: comment["createdAt"])
    return comments


def create_comment(comment_data: dict[str, Any]) -> dict[str, Any]:
    """Create comment data and return the created payload."""
    comment = {
        "id": comment_data.get("id", generate_id()),
        "postId": comment_data["postId"],
        "userId": comment_data["userId"],
        "text": comment_data["text"],
        "createdAt": comment_data.get("createdAt", now_iso()),
        "updatedAt": comment_data.get("updatedAt", now_iso()),
    }
    _comments().append(comment)
    persist()
    return copy_record(comment)


def delete_comment(comment_id: str) -> bool:
    """Delete comment data for the requested context."""
    comments = _comments()
    index = next((i for i, comment in enumerate(comments) if comment["id"] == comment_id), None)
    if index is None:
        return False
    del comments[index]
    persist()
    return True


def get_comment_count_by_post_id(post_id: str) -> int:
    """Return comment count by post id data for the requested context."""
    return sum(1 for comment in _comments() if comment["postId"] == post_id)


def delete_comments_by_post_id(post_id: str) -> None:
    """Delete comments by post id data for the requested context."""
    db()["comments"] = [comment for comment in _comments() if comment["postId"] != post_id]
    persist()

