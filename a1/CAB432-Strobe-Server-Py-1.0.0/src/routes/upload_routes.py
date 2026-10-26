from fastapi import APIRouter, Body, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse

from ..controllers.upload_controller import get_upload_url_controller, upload_file_controller
from ..middleware.auth import authenticate

router = APIRouter()


@router.post("/url")
async def upload_url(payload: dict = Body(...), current_user: dict = Depends(authenticate)) -> dict:
    """POST /v1/uploads/url: Create one-time upload URL data for an authenticated user."""
    status_code, body = get_upload_url_controller(current_user["userId"], payload)
    return JSONResponse(status_code=status_code, content=body)


@router.put("/{user_id}/{post_id}/{file_id}")
async def upload_file(user_id: str, post_id: str, file_id: str, file: UploadFile = File(...), current_user: dict = Depends(authenticate)) -> dict:
    """PUT /v1/uploads/{user_id}/{post_id}/{file_id}: Upload a file for the authenticated user."""
    status_code, body = await upload_file_controller(user_id, post_id, file_id, file)
    return JSONResponse(status_code=status_code, content=body)
