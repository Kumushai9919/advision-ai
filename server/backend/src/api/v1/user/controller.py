from fastapi import APIRouter, HTTPException, status, Query
from src.core.logger import logger
from src.database.core import DbSession
from typing import Optional
from uuid import UUID
from .schema import (
    UserResponseData,
    UserDeleteResponse,
    UserListApiResponse,
    UserUpdateResponse,
    UserUpdateSchema,
    FaceListBase,
    FaceListApiResponse,
    FaceDeleteResponse
)
from src.core.exception import (
    UserNotFoundError,
    FaceNotFoundError,
    InternalError
)
from src.service.user_service import UserService
from src.service.face_service import FaceService
from src.database.core import DbSession

router = APIRouter()

@router.get(
    "/",
    response_model=UserListApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Get users list",
    description="Retrieve paginated list of users. Can be filtered by organization."
)
async def get_users(
    db: DbSession,
    org_id: Optional[str] = Query(
        None, 
        description="Filter users by organization ID"
    ),
    page: int = Query(
        1, 
        ge=1, 
        description="Page number (minimum: 1)"
    ),
    limit: int = Query(
        20, 
        ge=1, 
        le=100, 
        description="Items per page (minimum: 1, maximum: 100)"
    )
):
    """
    Retrieve paginated list of users.
    
    - **org_id** (optional): Filter by organization ID
    - **page**: Page number (default: 1)
    - **limit**: Number of items per page (default: 20, max: 100)
    
    Returns user list with pagination metadata including:
    - Total number of users
    - Total pages
    - Current page
    - Has next/previous page indicators
    """
    try:
        service = UserService(db)
        
        # Get users based on org_id filter
        if org_id:
            users, pagination = service.get_by_org_paginated(
                org_id=org_id,
                page=page,
                limit=limit
            )
        else:
            users, pagination = service.get_all_paginated(
                page=page,
                limit=limit
            )
        
        return UserListApiResponse(
            success=True,
            data=UserResponseData(
                users=users,
                pagination=pagination
            )
        )
        
    except ValueError as e:
        logger.error(f"ValueError in get_users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )

@router.patch(
    "/{user_id}",
    response_model=UserUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user information"
)
async def update_user(
    user_id: str,
    user_data: UserUpdateSchema,
    db: DbSession
):
    """
    Update user information (partial update)
    
    - **user_id**: User identifier
    - **org_id** (optional): New organization ID
    - **is_active** (optional): New active status
    
    At least one field must be provided.
    """
    try:
        service = UserService(db)
        updated_user = service.update(user_id, user_data)
        
        return UserUpdateResponse(
            success=True,
            data=updated_user
        )
        
    except (UserNotFoundError, ValueError):
        raise
        
    except Exception as e:
        logger.error(f"Error in update_user endpoint: {e}", exc_info=True)
        raise InternalError("사용자 정보 업데이트에 실패했습니다.")

@router.delete(
    "/{user_id}",
    response_model=UserDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete user"
)
async def delete_user(
    user_id: str,
    db: DbSession
):
    """Delete a user from the system"""
    try:
        service = UserService(db)
        deleted_user = service.delete(user_id)
        
        return UserDeleteResponse(
            success=True,
            data=deleted_user
        )
        
    except (UserNotFoundError, InternalError):
        raise
        
    except Exception as e:
        logger.error(f"Error in delete_user endpoint: {e}", exc_info=True)
        raise InternalError("사용자 삭제에 실패했습니다.")

@router.get(
    "/{user_id}/faces",
    response_model=FaceListApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all faces for a user"
)
async def get_user_faces(
    db: DbSession,
    user_id: str,
    page: int = Query(
        1, 
        ge=1, 
        description="Page number (minimum: 1)"
    ),
    limit: int = Query(
        20, 
        ge=1, 
        le=100, 
        description="Items per page (minimum: 1, maximum: 100)"
    )
):
    """Get all face records for a user"""
    service = FaceService(db)
    service_user = UserService(db)
    
    try:
        logger.info(f"Fetching faces for user {user_id}, page {page}, limit {limit}")
        
        user = service_user.get_by_user_id(user_id)
        if not user:
            raise UserNotFoundError()
        
        faces, pagination = service.get_by_user_paginated(
            user_id=user.id, 
            page=page, 
            limit=limit
        )
        
        return FaceListApiResponse(
            success=True,
            data=FaceListBase(
                user_id=user.user_id,
                org_id=user.org_id,
                total_faces=pagination.total_items,
                faces=faces,
                pagination=pagination
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in get_user_faces endpoint: {str(e)}", exc_info=True)
        raise FaceNotFoundError()

@router.delete(
    "/{user_id}/faces",
    response_model=UserDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete all faces for a user"
)
async def delete_all_faces(
    user_id: str,
    db: DbSession
):
    """Delete all faces for a user"""
    try:
        service = UserService(db)
        deleted_user = service.delete(user_id)
        
        return UserDeleteResponse(
            success=True,
            data=deleted_user
        )
        
    except (UserNotFoundError, InternalError):
        raise
        
    except Exception as e:
        logger.error(f"Error in delete_user endpoint: {e}", exc_info=True)
        raise InternalError("사용자 삭제에 실패했습니다.")

@router.delete(
    "/{user_id}/faces/{face_id}",
    response_model=FaceDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a specific face"
)
async def delete_user_face(
    user_id: str,
    face_id: UUID,
    db: DbSession
):
    """Delete a specific face record for a user"""
    try:
        user_service = UserService(db)
        face_service = FaceService(db)
        
        # Get user first
        user = user_service.get_by_user_id(user_id)
        if not user:
            raise UserNotFoundError()

        # Delete face
        face_info = face_service.delete(user, face_id)

        return FaceDeleteResponse(
            success=True,
            data=face_info
        )
        
    except (UserNotFoundError, FaceNotFoundError):
        raise
        
    except Exception as e:
        logger.error(f"Error deleting face {face_id} for user {user_id}: {e}", exc_info=True)
        raise InternalError("Failed to delete face")
