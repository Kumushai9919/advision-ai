from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List


class UserFaceData(BaseModel):
    """User face data structure"""
    user_id: str = Field(..., description="User identifier")
    faces: List[str] = Field(..., description="List of face IDs for this user")


class FaceData(BaseModel):
    """Face data structure"""
    face_id: str = Field(..., description="Face identifier")
    user_id: str = Field(..., description="User identifier this face belongs to")


class ExportData(BaseModel):
    """Complete export data structure"""
    companies: Dict[str, dict] = Field(
        ...,
        description="Mapping of company/organization IDs to metadata objects"
    )
    users: Dict[str, Dict[str, UserFaceData]] = Field(
        ..., 
        description="Nested dictionary: company_id -> user_id -> user face data"
    )
    faces: Dict[str, List[FaceData]] = Field(
        ...,
        description="Dictionary mapping company_id to list of face data"
    )
    embeddings: Dict[str, List[float]] = Field(
        ..., 
        description="Dictionary mapping face_id to embedding vector"
    )


class ExportResponse(BaseModel):
    """Response for export endpoint"""
    success: bool = Field(default=True)
    data: ExportData
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "companies": {"company_123": {}, "company_456": {}},
                "users": {
                    "company_123": {
                        "user_001": {
                            "user_id": "user_001",
                            "faces": ["face_001", "face_002"]
                        }
                    }
                },
                "faces": {
                    "company_123": [
                        {
                            "face_id": "face_001",
                            "user_id": "user_001"
                        },
                        {
                            "face_id": "face_002",
                            "user_id": "user_001"
                        }
                    ]
                },
                "embeddings": {
                    "face_001": [0.123, -0.456, 0.789]
                }
            }
        }
    })