from fastapi import APIRouter, status, Depends, Query
from sqlalchemy.orm import Session
from typing import Annotated
from datetime import datetime
from src.core.timezone import now_kst
from src.database.core import get_db
from src.service.user_service import UserService
from src.core.logger import logger
from .schema import (
    OrgListApiResponse,
    OrgDetailApiResponse,
    OrgDeleteResponse,
    OrgListData,
    OrgDetailData,
    OrgDeleteData
)
from src.core.exception import OrgNotFoundError, InternalError

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/",
    response_model=OrgListApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all organizations",
    description="Retrieve paginated list of all organizations with user and face counts"
)
async def get_organizations(
    db: DbSession,
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
    Retrieve paginated list of organizations with statistics.
    """
    try:
        service = UserService(db)
        orgs_data, pagination = service.get_all_organizations_paginated(
            page=page,
            limit=limit
        )
        
        return OrgListApiResponse(
            success=True,
            data=OrgListData(
                organizations=orgs_data,
                pagination=pagination
            )
        )
        
    except ValueError as e:
        logger.error(f"ValueError in get_organizations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving organizations: {e}", exc_info=True)
        raise InternalError("조직 목록을 가져오는 중 오류가 발생했습니다.")

@router.delete(
    "/{org_id}",
    response_model=OrgDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete organization",
    description="Delete an organization and all its users, faces, and images"
)
async def delete_organization(
    org_id: str,
    db: DbSession
):
    """
    Delete an organization and all associated data.
    """
    try:
        service = UserService(db)
        deleted_users = service.delete_org(org_id)

        if deleted_users == 0:
            raise OrgNotFoundError(f"조직 {org_id}을(를) 찾을 수 없습니다.")
        
        logger.info(f"Successfully deleted organization {org_id} faces")
        
        return OrgDeleteResponse(
            success=True,
            data=OrgDeleteData(
                org_id=org_id,
                message="조직이 성공적으로 삭제되었습니다.",
                deleted_at=now_kst()
            )
        )
        
    except OrgNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error deleting organization {org_id}: {e}", exc_info=True)
        raise InternalError("조직 삭제 중 오류가 발생했습니다.")