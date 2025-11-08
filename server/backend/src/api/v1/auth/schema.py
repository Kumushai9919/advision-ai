from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============= Schemas =============
class FaceRegisterData(BaseModel):
    face_id: str 
    user_id: str
    org_id: str 
    message: str
    registered_at: datetime

class FaceRegisterResponse(BaseModel):
    success: bool = True
    data: FaceRegisterData

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "face_id": "876fqc5aa055f8e48226459e8",
                "user_id": "6891c34f055f8e48226459e5",
                "org_id": "4292c451055f8e4822645a02",
                "message": "사용자 얼굴이 성공적으로 등록되었습니다.",
                "registered_at": "2025-09-19T09:30:00Z"
            }
        }
    })
    
class FaceDetectData(BaseModel):
    user_id: str
    org_id: str
    confidence: float
    message: str
    detected_at: datetime

class FaceDetectResponse(BaseModel):
    success: bool = True
    data: FaceDetectData

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "user_id": "6891c34f055f8e48226459e5",
                "org_id": "4292c451055f8e4822645a02",
                "bbox": {"x": 100, "y": 150, "width": 200, "height": 200},
                "confidence": 0.98,
                "message": "얼굴이 성공적으로 인식되었습니다.",
                "detected_at": "2025-09-19T10:00:00Z"
            }
        }
    })


# ============= Advertise Schemas =============
class ViewerRegisterRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image")
    start_time: str = Field(..., description="Start time as datetime string")
    end_time: str = Field(..., description="End time as datetime string")
    duration: float = Field(..., description="Duration in seconds", gt=0)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "image_base64": "/9j/4AAQSkZJRgABAQEAYABgAAD...",
            "start_time": "2025-11-09T14:30:00",
            "end_time": "2025-11-09T14:35:00",
            "duration": 300.0
        }
    })


class ViewerRegisterData(BaseModel):
    face_id: str
    user_id: str
    org_id: str
    start_time: str
    end_time: str
    duration: float
    image_url: str
    registered_at: str
    message: str


class ViewerRegisterResponse(BaseModel):
    success: bool = True
    data: ViewerRegisterData

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "face_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "user_id": "viewer_12345678-1234-1234-1234-123456789012",
                "org_id": "default_org",
                "start_time": "2025-11-09T14:30:00",
                "end_time": "2025-11-09T14:35:00",
                "duration": 300.0,
                "image_url": "https://storage.example.com/faces/image.jpg",
                "registered_at": "2025-11-09T14:35:01",
                "message": "Viewer registered successfully with face embedding"
            }
        }
    })


class FacilityDetectionRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image")
    start_time: str = Field(..., description="Start time as datetime string")
    end_time: str = Field(..., description="End time as datetime string")
    duration: float = Field(..., description="Duration in seconds", gt=0)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "image_base64": "/9j/4AAQSkZJRgABAQEAYABgAAD...",
            "start_time": "2025-11-09T15:00:00",
            "end_time": "2025-11-09T15:02:00",
            "duration": 120.0
        }
    })


class FacilityDetectionData(BaseModel):
    user_id: Optional[str] = None
    org_id: str
    facility_id: str
    confidence: Optional[float] = None
    bbox: Optional[List[int]] = None
    visit_count: Optional[int] = None
    start_time: str
    end_time: str
    duration: float
    detection_id: Optional[int] = None
    detected_at: Optional[str] = None
    message: str


class FacilityDetectionResponse(BaseModel):
    success: bool
    data: FacilityDetectionData

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "user_id": "viewer_12345678-1234-1234-1234-123456789012",
                "org_id": "default_org",
                "facility_id": "facility_001",
                "confidence": 0.96,
                "bbox": [100, 150, 200, 200],
                "start_time": "2025-11-09T15:00:00",
                "end_time": "2025-11-09T15:02:00",
                "duration": 120.0,
                "detection_id": 42,
                "detected_at": "2025-11-09T15:02:01",
                "message": "Face detected successfully"
            }
        }
    })
