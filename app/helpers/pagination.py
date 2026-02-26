from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Query

T = TypeVar('T')

class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = 1
    page_size: int = 10
    
    @property
    def skip(self) -> int:
        """Calculate skip value for pagination"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit value"""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int):
        """Create paginated response"""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


def paginate_query(query: Query, page: int = 1, page_size: int = 10) -> tuple[List, int]:
    """
    Paginate a SQLAlchemy query
    Returns: (items, total_count)
    """
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total
