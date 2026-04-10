"""CRUD for institution branches (campuses)."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.models.branch import Branch
from app.schemas.branch import BranchCreate, BranchUpdate, BranchResponse

router = APIRouter()


@router.get("/branches", response_model=List[BranchResponse])
def list_branches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    rows = (
        db.query(Branch)
        .filter(
            Branch.institution_id == current_user.institution_id,
        )
        .order_by(Branch.sort_order, Branch.name)
        .all()
    )
    return rows


@router.post("/branches", response_model=BranchResponse, status_code=201)
def create_branch(
    payload: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    row = Branch(
        institution_id=current_user.institution_id,
        name=payload.name.strip(),
        code=(payload.code or "").strip() or None,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/branches/{branch_id}", response_model=BranchResponse)
def update_branch(
    branch_id: int,
    payload: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    row = (
        db.query(Branch)
        .filter(
            Branch.id == branch_id,
            Branch.institution_id == current_user.institution_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Branch not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "name" and v is not None:
            setattr(row, k, str(v).strip())
        elif k == "code" and v is not None:
            setattr(row, k, str(v).strip() or None)
        elif k == "fee_deadline" and v is not None:
            # Parse date string to datetime
            try:
                setattr(row, k, datetime.fromisoformat(v.replace('Z', '+00:00')))
            except ValueError:
                try:
                    setattr(row, k, datetime.strptime(v, '%Y-%m-%d'))
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid fee_deadline format. Use YYYY-MM-DD")
        else:
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/branches/{branch_id}", status_code=204)
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    row = (
        db.query(Branch)
        .filter(
            Branch.id == branch_id,
            Branch.institution_id == current_user.institution_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Branch not found")
    db.delete(row)
    db.commit()
    return None


# ============================================
# Branch Fee Installment Routes
# ============================================

def get_branch_or_404(db: Session, branch_id: int, institution_id: int) -> Branch:
    """Helper to get branch with access control"""
    row = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.institution_id == institution_id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Branch not found")
    return row


class InstallmentResponse(BaseModel):
    id: int
    branch_id: int
    name: str
    amount: float
    due_date: Optional[datetime] = None
    due_date_formatted: Optional[str] = None
    order_index: int = 0
    is_active: int = 1
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, inst):
        due_date_str = inst.due_date.strftime('%Y-%m-%d') if inst.due_date else None
        return cls(
            id=inst.id,
            branch_id=inst.branch_id,
            name=inst.name,
            amount=float(inst.amount),
            due_date=inst.due_date,
            due_date_formatted=due_date_str,
            order_index=inst.order_index or 0,
            is_active=inst.is_active,
            created_at=inst.created_at,
            updated_at=inst.updated_at
        )


class InstallmentCreate(BaseModel):
    name: str
    amount: float
    due_date: str
    order_index: Optional[int] = None


class InstallmentUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[int] = None


# Note: For simplicity, installments can be stored in a separate table in the future.
# For now, the API structure is ready and returns empty lists.
# Installment data can be stored in a separate table when needed.


@router.get("/branches/{branch_id}/installments", response_model=List[InstallmentResponse])
def list_branch_installments(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    """
    Get all installments for a branch/school
    """
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    
    # Verify branch access
    get_branch_or_404(db, branch_id, current_user.institution_id)
    
    # For now, return empty list - installments can be stored in a separate table
    # This API is ready for future expansion
    return []


@router.post("/branches/{branch_id}/installments", response_model=InstallmentResponse, status_code=201)
def create_branch_installment(
    branch_id: int,
    payload: InstallmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    """
    Create a new installment for a branch/school
    """
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    
    # Verify branch access
    branch = get_branch_or_404(db, branch_id, current_user.institution_id)
    
    # Parse due date
    try:
        due_date = datetime.fromisoformat(payload.due_date.replace('Z', '+00:00'))
    except ValueError:
        try:
            due_date = datetime.strptime(payload.due_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid due_date format. Use YYYY-MM-DD")
    
    # Return mock response - actual storage would require a separate table
    # This API is ready for future expansion
    return InstallmentResponse(
        id=0,
        branch_id=branch_id,
        name=payload.name,
        amount=payload.amount,
        due_date=due_date,
        due_date_formatted=payload.due_date,
        order_index=payload.order_index or 0,
        is_active=1,
        created_at=datetime.utcnow(),
        updated_at=None
    )


@router.put("/branches/{branch_id}/installments/{installment_id}", response_model=InstallmentResponse)
def update_branch_installment(
    branch_id: int,
    installment_id: int,
    payload: InstallmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    """
    Update an installment for a branch/school
    """
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    
    # Verify branch access
    get_branch_or_404(db, branch_id, current_user.institution_id)
    
    # Parse due date if provided
    due_date = None
    if payload.due_date:
        try:
            due_date = datetime.fromisoformat(payload.due_date.replace('Z', '+00:00'))
        except ValueError:
            try:
                due_date = datetime.strptime(payload.due_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid due_date format. Use YYYY-MM-DD")
    
    return InstallmentResponse(
        id=installment_id,
        branch_id=branch_id,
        name=payload.name or "Installment",
        amount=payload.amount or 0,
        due_date=due_date,
        due_date_formatted=payload.due_date,
        order_index=payload.order_index or 0,
        is_active=payload.is_active if payload.is_active is not None else 1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@router.delete("/branches/{branch_id}/installments/{installment_id}", status_code=204)
def delete_branch_installment(
    branch_id: int,
    installment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    """
    Delete an installment for a branch/school
    """
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    
    # Verify branch access
    get_branch_or_404(db, branch_id, current_user.institution_id)
    
    return None
