from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


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

    