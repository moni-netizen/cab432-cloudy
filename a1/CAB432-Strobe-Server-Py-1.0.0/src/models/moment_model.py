from __future__ import annotations

from typing import Any

from ..utils.id_generator import generate_id
from .common import copy_record, db, now_iso, persist


def _moments() -> list[dict[str, Any]]:
    """Return the mutable moments collection from the database."""
    return db()["moments"]


def create_moment(moment_data: dict[str, Any]) -> dict[str, Any]:
    """Create moment data and return the created payload."""
    moment = {
        "id": moment_data.get("id", generate_id()),
        "userId": moment_data["userId"],
        "imageUrl": moment_data["imageUrl"],
        "caption": moment_data.get("caption", ""),
        "status": moment_data.get("status", "active"),
        "hiddenBy": moment_data.get("hiddenBy"),
        "hiddenAt": moment_data.get("hiddenAt"),
        "archivedAt": moment_data.get("archivedAt"),
        "createdAt": moment_data.get("createdAt", now_iso()),
        "expiresAt": moment_data.get("expiresAt"),
        "updatedAt": moment_data.get("updatedAt", now_iso()),
    }
    _moments().append(moment)
    persist()
    return copy_record(moment)


def find_moment_by_id(moment_id: str) -> dict[str, Any] | None:
    """Find moment by id and return it when available."""
    return copy_record(next((moment for moment in _moments() if moment["id"] == moment_id), None))


def update_moment(moment_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update moment and return the updated payload."""
    for moment in _moments():
        if moment["id"] == moment_id:
            for key, value in updates.items():
                if value is not None and key != "id":
                    moment[key] = value
            moment["updatedAt"] = now_iso()
            persist()
            return copy_record(moment)
    return None


def delete_moment(moment_id: str) -> bool:
    """Delete moment data for the requested context."""
    moments = _moments()
    index = next((i for i, moment in enumerate(moments) if moment["id"] == moment_id), None)
    if index is None:
        return False
    del moments[index]
    persist()
    return True


def get_moments_by_user_ids(user_ids: list[str]) -> list[dict[str, Any]]:
    """Return moments by user ids data for the requested context."""
    moments = [copy_record(moment) for moment in _moments() if moment["userId"] in user_ids]
    moments.sort(key=lambda moment: moment["createdAt"], reverse=True)
    return moments


def get_moments_by_user_id(user_id: str) -> list[dict[str, Any]]:
    """Return moments by user id data for the requested context."""
    return get_moments_by_user_ids([user_id])


def delete_moments_by_user_id(user_id: str) -> None:
    """Delete moments by user id data for the requested context."""
    db()["moments"] = [moment for moment in _moments() if moment["userId"] != user_id]
    persist()

