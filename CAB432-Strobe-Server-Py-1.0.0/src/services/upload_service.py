from __future__ import annotations

import os
from pathlib import Path

from fastapi import UploadFile

from ..config.constants import MAX_UPLOAD_SIZE, VALID_IMAGE_MIMETYPES
from ..config.settings import settings
from ..errors import not_found_error, validation_error
from ..utils.id_generator import generate_short_id


def get_upload_url(user_id: str, post_id: str) -> dict:
    """Generate one-time upload route metadata for a post asset."""
    if not post_id:
        raise validation_error("Post ID is required")
    file_id = generate_short_id()
    return {
        "uploadUrl": settings.to_public_url(f"/v1/uploads/{user_id}/{post_id}/{file_id}"),
        "fileId": file_id,
    }


async def store_uploaded_file(user_id: str, post_id: str, file_id: str, file: UploadFile) -> dict:
    """Validate and persist uploaded image file, then return file metadata."""
    if file.content_type not in VALID_IMAGE_MIMETYPES:
        raise validation_error("Unsupported file type")

    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise validation_error("File is too large")

    extension = VALID_IMAGE_MIMETYPES[file.content_type]
    target_dir = Path(settings.uploads_dir) / user_id / post_id
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{file_id}.{extension}"
    target_path = target_dir / filename
    target_path.write_bytes(data)
    return {
        "fileId": file_id,
        "url": settings.to_public_url(f"/uploads/{user_id}/{post_id}/{filename}"),
        "size": len(data),
        "mimetype": file.content_type,
    }


def delete_uploaded_file(file_id: str) -> bool:
    """Delete an uploaded file by ID if present on disk."""
    root = Path(settings.uploads_dir)
    if not root.exists():
        return False
    for path in root.rglob(f"{file_id}.*"):
        path.unlink(missing_ok=True)
        return True
    return False


def get_file_url(file_id: str) -> str | None:
    """Resolve public uploads URL for a stored file ID."""
    root = Path(settings.uploads_dir)
    for path in root.rglob(f"{file_id}.*"):
        return settings.to_public_url(f"/uploads/{path.relative_to(root).as_posix()}")
    return None

