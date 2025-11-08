from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from datetime import datetime

from src.service.advertise_service import AdvertiseService
from src.database.core import DbSession
from src.core.exception import InternalError
from src.core.logger import logger
from .schema import AnalyticsResponse

router = APIRouter()


@router.get(
    "/",
    response_model=AnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get analytics data",
    description="Retrieve analytics data for an organization including summary statistics and daily history"
)
async def get_analytics(
    db: DbSession,
    org_id: str = Query(..., description="Organization ID"),
    start_date: Optional[str] = Query(
        None,
        description="Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). Defaults to 7 days ago."
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). Defaults to now."
    )
):
    """
    Get analytics data for an organization
    
    Returns analytics including:
    - Summary: total viewers, new viewers, customers, average view time with percentage differences
    - Daily history: day-by-day breakdown of viewers, customers, and average view time
    
    Args:
        org_id: Organization ID (required)
        start_date: Optional start date (defaults to 7 days ago)
        end_date: Optional end date (defaults to now)
    
    Returns:
        AnalyticsResponse with summary and daily history
    """
    try:
        service = AdvertiseService(db)
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                # Try parsing as ISO format
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Try parsing as date only
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid start_date format. Use YYYY-MM-DD or ISO format."
                    )
        
        if end_date:
            try:
                # Try parsing as ISO format
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Try parsing as date only
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid end_date format. Use YYYY-MM-DD or ISO format."
                    )
        
        result = service.get_analytics(
            org_id=org_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return AnalyticsResponse(**result)
    
    except InternalError as e:
        logger.error(f"Internal error getting analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )

