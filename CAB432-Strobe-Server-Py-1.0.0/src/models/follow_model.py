from __future__ import annotations

from typing import Any

from ..utils.id_generator import generate_id
from .common import copy_record, db, now_iso, persist


def _follows() -> list[dict[str, Any]]:
    """Return the mutable follows collection from the database."""
    return db()["follows"]


def find_follow(follower_id: str, followee_id: str) -> dict[str, Any] | None:
    """Find follow and return it when available."""
    return copy_record(next((follow for follow in _follows() if follow["followerId"] == follower_id and follow["followeeId"] == followee_id), None))


def is_following(follower_id: str | None, followee_id: str) -> bool:
    """Return whether following is true for the current context."""
    if not follower_id:
        return False
    return any(follow["followerId"] == follower_id and follow["followeeId"] == followee_id for follow in _follows())


def get_following(user_id: str) -> list[str]:
    """Return following data for the requested context."""
    return [follow["followeeId"] for follow in _follows() if follow["followerId"] == user_id]


def get_followers(user_id: str) -> list[str]:
    """Return followers data for the requested context."""
    return [follow["followerId"] for follow in _follows() if follow["followeeId"] == user_id]


def get_following_count(user_id: str) -> int:
    """Return following count data for the requested context."""
    return sum(1 for follow in _follows() if follow["followerId"] == user_id)


def get_follower_count(user_id: str) -> int:
    """Return follower count data for the requested context."""
    return sum(1 for follow in _follows() if follow["followeeId"] == user_id)


def create_follow(follow_data: dict[str, Any]) -> dict[str, Any]:
    """Create follow data and return the created payload."""
    follow = {
        "id": follow_data.get("id", generate_id()),
        "followerId": follow_data["followerId"],
        "followeeId": follow_data["followeeId"],
        "createdAt": follow_data.get("createdAt", now_iso()),
    }
    _follows().append(follow)
    persist()
    return copy_record(follow)


def remove_follow(follower_id: str, followee_id: str) -> bool:
    """Remove follow data for the requested context."""
    follows = _follows()
    index = next((i for i, follow in enumerate(follows) if follow["followerId"] == follower_id and follow["followeeId"] == followee_id), None)
    if index is None:
        return False
    del follows[index]
    persist()
    return True


def remove_follows_by_user_id(user_id: str) -> None:
    """Remove follows by user id data for the requested context."""
    db()["follows"] = [follow for follow in _follows() if follow["followerId"] != user_id and follow["followeeId"] != user_id]
    persist()

