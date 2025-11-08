from pydantic import BaseModel, Field, ConfigDict
from typing import List
from datetime import datetime
from src.core.pagination import PaginationMeta


class OrgResponse(BaseModel):
    """Single organization response with statistics"""
    org_id: str = Field(..., description="Organization identifier")
    user_count: int = Field(..., description="Number of users in organization")
    face_count: int = Field(..., description="Number of faces in organization")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "org_id": "company_123",
            "user_count": 150,
            "face_count": 450
        }
    })


class OrgListData(BaseModel):
    """Data containing list of organizations with pagination"""
    organizations: List[OrgResponse] = Field(..., description="List of organizations")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


class OrgListApiResponse(BaseModel):
    """API response for organization list"""
    success: bool = Field(default=True)
    data: OrgListData
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "organizations": [
                    {
                        "org_id": "company_123",
                        "user_count": 150,
                        "face_count": 450
                    },
                    {
                        "org_id": "company_456",
                        "user_count": 75,
                        "face_count": 200
                    }
                ],
                "pagination": {
                    "page": 1,
                    "limit": 20,
                    "total_items": 50,
                    "total_pages": 3,
                    "has_next": True,
                    "has_prev": False
                }
            }
        }
    })


class OrgDetailData(BaseModel):
    """Single organization detail data"""
    org_id: str = Field(..., description="Organization identifier")
    user_count: int = Field(..., description="Number of users in organization")
    face_count: int = Field(..., description="Number of faces in organization")


class OrgDetailApiResponse(BaseModel):
    """API response for single organization"""
    success: bool = Field(default=True)
    data: OrgDetailData
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "org_id": "company_123",
                "user_count": 150,
                "face_count": 450
            }
        }
    })


class OrgDeleteData(BaseModel):
    """Data returned after deleting an organization"""
    org_id: str = Field(..., description="Deleted organization identifier")
    message: str = Field(..., description="Success message")
    deleted_at: datetime = Field(..., description="Timestamp when organization was deleted")


class OrgDeleteResponse(BaseModel):
    """Response after deleting an organization"""
    success: bool = Field(default=True)
    data: OrgDeleteData
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "org_id": "company_123",
                "message": "조직이 성공적으로 삭제되었습니다.",
                "deleted_at": "2025-10-21T10:00:00Z"
            }
        }
    })