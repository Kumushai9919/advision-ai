from fastapi import APIRouter, Query
from typing import Optional

from src.database.core import DbSession
from src.service.worker_service import WorkerService
from .schema import ExportResponse
from src.core.exception import UserNotFoundError, InternalError
from src.core.logger import logger

router = APIRouter()

@router.get(
    "/",
    response_model=ExportResponse,
    summary="Export all face recognition data",
    description="Export all companies, users, and face embeddings in JSON format"
)
async def worker_init(
    db: DbSession
):
    """
    Export face recognition data
    Returns structured JSON with companies, users, and embeddings.
    """
    try:
        service = WorkerService(db)
        
        export_data = service.init_worker()
        
        return ExportResponse(
            success=True,
            data=export_data
        )
        
    except Exception as e:
        logger.error(f"Error in export endpoint: {e}", exc_info=True)
        raise InternalError("데이터 내보내기에 실패했습니다.")