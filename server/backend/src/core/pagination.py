from typing import List, TypeVar, Generic
from math import ceil
from sqlalchemy.orm import Query
from pydantic import BaseModel, Field

T = TypeVar('T')

class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    pagination: PaginationMeta


class PaginationHelper:
    """Helper class for handling pagination"""
    
    DEFAULT_PAGE = 1
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100
    
    @staticmethod
    def validate_params(page: int = 1, limit: int = 20) -> tuple[int, int]:
        """
        Validate and normalize pagination parameters
        
        Args:
            page: Page number (must be >= 1)
            limit: Items per page (must be between 1 and MAX_LIMIT)
            
        Returns:
            Tuple of (validated_page, validated_limit)
        """
        page = max(1, page)
        limit = max(1, min(limit, PaginationHelper.MAX_LIMIT))
        return page, limit
    
    @staticmethod
    def calculate_offset(page: int, limit: int) -> int:
        """Calculate SQL offset from page and limit"""
        return (page - 1) * limit
    
    @staticmethod
    def create_meta(
        page: int,
        limit: int,
        total_items: int
    ) -> PaginationMeta:
        """
        Create pagination metadata
        
        Args:
            page: Current page number
            limit: Items per page
            total_items: Total number of items
            
        Returns:
            PaginationMeta object with calculated values
        """
        total_pages = ceil(total_items / limit) if limit > 0 else 0
        
        return PaginationMeta(
            page=page,
            limit=limit,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    
    @staticmethod
    def paginate_query(
        query: Query,
        page: int = 1,
        limit: int = 20
    ) -> tuple[List, PaginationMeta]:
        """
        Paginate a SQLAlchemy query
        
        Args:
            query: SQLAlchemy query object
            page: Page number
            limit: Items per page
            
        Returns:
            Tuple of (items, pagination_meta)
        """
        # Validate parameters
        page, limit = PaginationHelper.validate_params(page, limit)
        
        total_items = query.count()
        offset = PaginationHelper.calculate_offset(page, limit)
        items = query.offset(offset).limit(limit).all()
        pagination_meta = PaginationHelper.create_meta(page, limit, total_items)
        
        return items, pagination_meta
    
    @staticmethod
    def paginate_list(
        items: List[T],
        page: int = 1,
        limit: int = 20
    ) -> tuple[List[T], PaginationMeta]:
        """
        Paginate a Python list (for in-memory pagination)
        
        Args:
            items: List of items to paginate
            page: Page number
            limit: Items per page
            
        Returns:
            Tuple of (paginated_items, pagination_meta)
        """
        page, limit = PaginationHelper.validate_params(page, limit)
        
        total_items = len(items)
        offset = PaginationHelper.calculate_offset(page, limit)
        paginated_items = items[offset:offset + limit]
        pagination_meta = PaginationHelper.create_meta(page, limit, total_items)
        
        return paginated_items, pagination_meta