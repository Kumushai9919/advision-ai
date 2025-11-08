from pydantic import BaseModel, Field, ConfigDict, validator, field_validator
from src.core.pagination import PaginationMeta
from typing import Optional, List
from uuid import UUID
from datetime import datetime

# ============ User Schemas =============
class UserBase(BaseModel):
    """Individual user data"""
    user_id: str = Field(..., description="External user identifier")
    org_id: str = Field(..., description="Organization identifier")
    face_count: int = Field(..., description="Number of faces registered")
    is_active: bool = Field(..., description="Whether the user is active")
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_db_model(cls, user, face_count: int = 0):
        """Create UserData from database model"""
        return cls(
            user_id=user.user_id,
            org_id=user.org_id,
            face_count=face_count,
            is_active=user.is_active
        )

class UserResponseData(BaseModel):
    """Response data containing users and pagination"""
    users: List[UserBase]
    pagination: PaginationMeta

class UserListApiResponse(BaseModel):
    """API response for user list"""
    success: bool = Field(default=True)
    data: UserResponseData
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "users": [
                    {
                        "user_id": "412qc5aa055f8e48226459e8",
                        "org_id": "6891c34f055f8e4822645914",
                        "face_count": 2,
                        "is_active": True,
                        "registered_at": "2025-09-19T10:00:00Z"
                    }
                ],
                "pagination": {
                    "page": 1,
                    "limit": 20,
                    "total_items": 150,
                    "total_pages": 8,
                    "has_next": True,
                    "has_prev": False
                }
            }
        }
    })

class UserUpdateSchema(BaseModel):
    """Schema for updating user information"""
    org_id: Optional[str] = Field(None, description="Organization identifier")
    is_active: Optional[bool] = Field(None, description="Whether the user is active")
    
    @field_validator('org_id')
    @classmethod
    def validate_org_id(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('org_id cannot be empty if provided')
        return v.strip() if v else v

class UserUpdateData(BaseModel):
    """Data returned after updating a user"""
    user_id: str = Field(..., description="User identifier")
    org_id: str = Field(..., description="Organization identifier")
    is_active: bool = Field(..., description="Whether the user is active")
    message: str = Field(..., description="Success message")
    updated_at: datetime = Field(..., description="Timestamp when the user was updated")

class UserUpdateResponse(BaseModel):
    """Response after updating a user"""
    success: bool = Field(default=True)
    data: UserUpdateData
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "user_id": "user123",
                "org_id": "org456",
                "is_active": True,
                "message": "사용자 정보가 성공적으로 업데이트되었습니다.",
                "updated_at": "2025-10-03T10:00:00Z"
            }
        }
    })

class UserDeleteData(BaseModel):
    """Data returned after deleting a user"""
    user_id: str = Field(..., description="Deleted user identifier")
    face_count: int = Field(..., description="Number of faces deleted")
    message: str = Field(..., description="Success message")
    deleted_at: datetime = Field(..., description="Timestamp when the face was registered")

class UserDeleteResponse(BaseModel):
    """Response after deleting a user"""
    success: bool = Field(default=True)
    data: UserDeleteData

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "user_id": "user123",
                "message": "User user123 successfully deleted",
                "deleted_at": "2025-09-19T10:00:00Z"
            }
        }
    })

# ============= Organization Schemas =============
class OrgBase(BaseModel):
    org_id: str = Field(..., description="Organization identifier")
    total_users: int = Field(..., description="Total number of users in the organization")
    users: List[UserBase] = Field(..., description="List of users in the organization")
    pagination: PaginationMeta

class OrgApiResponse(BaseModel):
    success: bool = Field(default=True)
    data: OrgBase
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "org_id": "6891c34f055f8e4822645914",
                "total_users": 50,
                "users": [
                    {
                        "user_id": "412qc5aa055f8e48226459e8",
                        "org_id": "6891c34f055f8e4822645914",
                        "face_count": 2,
                        "is_active": True,
                        "registered_at": "2025-09-19T10:00:00Z"
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

# ============= Face Schemas =============

class FaceBase(BaseModel):
    face_id: UUID = Field(..., description="Unique face identifier")
    image_url: str = Field(..., description="URL of the face image")
    registered_at: datetime = Field(..., description="Timestamp when the face was registered")
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_db_model(cls, face):
        """Create FaceBase from database model"""
        return cls(
            face_id=face.id,
            image_url=face.image_url,
            registered_at=face.registered_at
        )

class FaceListBase(BaseModel):
    user_id: str = Field(..., description="User identifier")
    org_id: str = Field(..., description="Organization identifier")
    total_faces: int = Field(..., description="Total number of faces for the user")
    faces: List[FaceBase] = Field(..., description="List of faces for the user")
    pagination: PaginationMeta
    
class FaceListApiResponse(BaseModel):
    success: bool = Field(default=True)
    data: FaceListBase
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "user_id": "412qc5aa055f8e48226459e8",
                "org_id": "6891c34f055f8e4822645914",
                "total_faces": 5,
                "faces": [
                    {
                        "face_id": "876fqc5aa055f8e48226459e8",
                        "image_url": "http://example.com/images/face1.jpg",
                        "registered_at": "2025-09-19T09:30:00Z"
                    }
                ],
                "pagination": {
                    "page": 1,
                    "limit": 20,
                    "total_items": 5,
                    "total_pages": 1,
                    "has_next": False,
                    "has_prev": False
                }
            }
        }
    })

class FaceDeleteData(BaseModel):
    """Data returned after deleting a face"""
    face_id: UUID = Field(..., description="Deleted face identifier")
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., description="Success message")

class FaceDeleteResponse(BaseModel):
    """Response after deleting a face"""
    success: bool = Field(default=True)
    data: FaceDeleteData
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {
                "face_id": "f7a8b9c0-1234-5678-90ab-cdef12345678",
                "user_id": "user123",
                "message": "Face deleted successfully"
            }
        }
    })




# ============= User Schemas =============
class UserCreateSchema(BaseModel):
    """Schema for creating a new user"""
    user_id: str = Field(..., description="External user identifier (must be unique)")
    org_id: str = Field(..., description="Organization identifier")
    is_active: bool = Field(default=True, description="Whether the user is active")
    
    @validator('user_id', 'org_id')
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()


class UserResponseSchema(BaseModel):
    """Schema for user responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: str
    org_id: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_orm(cls, obj):
        """Convert ORM object to response schema"""
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            org_id=obj.org_id,
            is_active=obj.is_active,
            created_at=getattr(obj, 'created_at', None),
            updated_at=getattr(obj, 'updated_at', None)
        )

# ============= Face Schemas =============

class FaceCreateSchema(BaseModel):
    """Schema for creating a face record"""
    image_url: str = Field(..., description="URL to the face image")
    embedding: List[float] = Field(..., description="Face embedding vector", min_items=1)
    
    @validator('image_url')
    def validate_image_url(cls, v):
        if not v or not v.strip():
            raise ValueError('image_url cannot be empty')
        return v.strip()
    
    @validator('embedding')
    def validate_embedding(cls, v):
        if not v:
            raise ValueError('embedding cannot be empty')
        if len(v) < 128:  # Common minimum embedding size
            raise ValueError('embedding vector too small')
        return v

class FaceResponseSchema(BaseModel):
    """Schema for face responses"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    image_url: str
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_orm(cls, obj):
        """Convert ORM object to response schema"""
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            image_url=obj.image_url,
            created_at=getattr(obj, 'created_at', None)
        )

class FaceWithEmbeddingSchema(FaceResponseSchema):
    """Schema for face with embedding data"""
    embedding: List[float]
    
    @classmethod
    def from_orm(cls, obj):
        """Convert ORM object with embedding to response schema"""
        return cls(
            id=obj.id,
            user_id=obj.user_id,
            image_url=obj.image_url,
            embedding=obj.embedding,
            created_at=getattr(obj, 'created_at', None)
        )

# ============= Additional Schemas =============

class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True

class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

class PaginationParams(BaseModel):
    """Pagination parameters"""
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of records to return")

class UserListResponse(BaseModel):
    """Response for user list with pagination"""
    users: List[UserResponseSchema]
    total: int
    skip: int
    limit: int

class FaceDataOnDemandSchema(BaseModel):
    """Schema for on-demand face processing"""
    user_id: str
    org_id: str
    embedding: List[float] = Field(..., description="Face embedding floats", min_items=1)
    metadata: Optional[dict] = Field(None, description="Additional metadata")