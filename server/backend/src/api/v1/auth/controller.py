from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
import asyncio
from src.service.auth_service import AuthService
from src.service.advertise_service import AdvertiseService
from src.database.core import DbSession
from src.core.config import get_settings
from pathlib import Path
from .schema import (
    FaceDetectResponse,
    ViewerRegisterResponse,
    ViewerRegisterData,
    FacilityDetectionResponse,
    FacilityDetectionData
)
from src.service.minio_service import MinIoService
from src.service.auth_service import AuthService
from concurrent.futures import ThreadPoolExecutor

from src.core.exception import (
    InvalidImageError,
    InternalError
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
    response = service.register(image_content, ext, user_id, org_id, "2025-11-09 04:07:03", "2025-11-09 04:07:03", 12)
    return response
  
@router.post("/viewer", status_code=status.HTTP_201_CREATED, response_model=ViewerRegisterResponse)
async def register_viewer(
    db: DbSession,
    image_base64: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    duration: int = Form(...),
    org_id: str = Form(default="default_org"),
):
    """
    Register a new viewer by creating a face embedding
    
    This endpoint receives viewer data from the viewer/client side and:
    1. Creates a new user with a unique ID
    2. Processes the face image and generates an embedding
    3. Stores the face in the database
    
    Args:
        image_base64: Base64 encoded image
        start_time: Start time as datetime string
        end_time: End time as datetime string  
        duration: Duration in seconds
        org_id: Organization ID (default: "default_org")
    
    Returns:
        ViewerRegisterResponse with registration details
    """
    try:
        service = AdvertiseService(db)
        result = service.register_viewer(
            image_base64=image_base64,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            org_id=org_id
        )
        
        return ViewerRegisterResponse(
            success=True,
            data=ViewerRegisterData(**result)
        )
    
    except InternalError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register viewer: {str(e)}"
        )

@router.post("/track", status_code=status.HTTP_200_OK, response_model=FacilityDetectionResponse)
async def detect_facility_visitors(
    db: DbSession,
    image_base64: str = Form(...),
    org_id: str = Form(...),
):
    """
    Detect a face at a facility and log the detection
    
    This endpoint receives data from facility/billboard cameras and:
    1. Attempts to recognize the face in the image
    2. If recognized, logs the detection event with duration
    3. Returns detection details including user_id and confidence
    
    Args:
        facility_id: Unique identifier for the facility/billboard
        image_base64: Base64 encoded image
        start_time: Start time as datetime string
        end_time: End time as datetime string
        duration: Duration in seconds
        org_id: Organization ID (default: "default_org")
    
    Returns:
        FacilityDetectionResponse with detection details or failure message
    """
    try:
        service = AdvertiseService(db)
        result = service.track_viewer(
            image_base64=image_base64,
            org_id=org_id
        )
        
        return FacilityDetectionResponse(
            success=result["success"],
            data=FacilityDetectionData(**result)
        )
    
    except InternalError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect facility visitor: {str(e)}"
        )

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