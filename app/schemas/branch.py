from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BranchBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: Optional[str] = Field(None, max_length=64)
    sort_order: int = 0
    is_active: bool = True


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    fee_amount: Optional[float] = Field(None, ge=0, description="Total fee amount for this school")
    fee_deadline: Optional[str] = Field(None, description="Final payment deadline (ISO format YYYY-MM-DD)")


class BranchResponse(BranchBase):
    id: int
    institution_id: int
    fee_amount: Optional[float] = None
    fee_deadline: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
