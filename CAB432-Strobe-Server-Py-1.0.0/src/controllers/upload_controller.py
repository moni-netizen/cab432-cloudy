from __future__ import annotations

from fastapi import UploadFile

from ..services.upload_service import get_upload_url, store_uploaded_file


def get_upload_url_controller(user_id: str, payload: dict) -> tuple[int, dict]:
    """Generate upload URL metadata and shape the HTTP response payload."""
    result = get_upload_url(user_id, payload.get("postId", ""))
    return 200, {"message": "Upload URL generated", **result}


async def upload_file_controller(user_id: str, post_id: str, file_id: str, file: UploadFile) -> tuple[int, dict]:
    """Store an uploaded file and shape the HTTP response payload."""
    uploaded = await store_uploaded_file(user_id, post_id, file_id, file)
    return 200, {"message": "File uploaded successfully", "file": uploaded}

