from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
import asyncio
from src.service.auth_service import AuthService
from src.database.core import DbSession
from src.core.config import get_settings
from pathlib import Path
from .schema import FaceDetectResponse
from src.service.minio_service import MinIoService
from src.service.auth_service import AuthService
from concurrent.futures import ThreadPoolExecutor

from src.core.exception import (
    InvalidImageError
)

# executor = ThreadPoolExecutor(max_workers=30)

minio_service = MinIoService()
router = APIRouter()

settings = get_settings()
MEDIA_DIR = Path(settings.MEDIA_ROOT)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED = {"image/jpeg": "jpg", "image/png": "png"}

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_face(
    db: DbSession,
    image: UploadFile = File(..., description="Image (jpg, png)"),
    user_id: str = Form(...),
    org_id: str  = Form(...),
):
    if image.content_type not in ALLOWED:
        raise InvalidImageError()
    
    service = AuthService(db)
    image_content = await image.read()
    ext = ALLOWED[image.content_type]
    response = service.register(image_content, ext, user_id, org_id)
    return response


@router.post("/detect", status_code=status.HTTP_200_OK, response_model=FaceDetectResponse)
async def detect_face(
    db: DbSession,
    image: UploadFile = File(..., description="Image (jpg, png)"),
    org_id: str = Form(...),
):
    """Detect and recognize a face in an image"""
    
    if image.content_type not in ALLOWED:
        raise InvalidImageError()
    
    service = AuthService(db)
    image_content = await image.read()
    response = service.detect(image_content, org_id)
    return response