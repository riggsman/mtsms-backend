"""
Fee Structure Routes - FastAPI endpoints for fee structure operations
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status, Path, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.schemas.fee_structure import (
    FeeStructureUpdate,
    FeeStructureResponse,
    FeeInstallmentCreate,
    FeeInstallmentUpdate,
    FeeInstallmentResponse,
    FeeStructureWithInstallmentsResponse
)
from app.apis.fee_structure import (
    get_fee_structure,
    update_fee_structure,
    get_installments,
    get_installment_by_id,
    create_installment,
    update_installment,
    delete_installment
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.dependencies.institutionDependency import get_institution_id_from_header
from app.models.user import User
from app.models.role import UserRole
from app.helpers.user_roles import user_has_role, user_is_system_admin
from decimal import Decimal

fee_structure = APIRouter()


def get_validated_tenant_id(
    tenant_id: int = Path(..., description="Tenant/School ID", gt=0),
    current_user: User = Depends(get_current_user_tenant)
) -> int:
    """
    Validate tenant_id against current user's institution
    """
    is_sys_admin = user_is_system_admin(current_user)
    
    if is_sys_admin:
        return tenant_id
    else:
        user_institution_id = current_user.institution_id
        
        if not user_institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an institution"
            )
        
        if tenant_id != user_institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You can only access fee structure for your institution (ID: {user_institution_id})"
            )
        
        return user_institution_id


# ============================================
# Fee Structure Endpoints (with tenant_id in path)
# ============================================

@fee_structure.get("/fee-structure/{tenant_id}", response_model=FeeStructureResponse)
def get_fee_structure_endpoint(
    tenant_id: int = Path(..., description="Tenant/School ID", gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Get fee structure for a specific tenant/school
    """
    validated_id = get_validated_tenant_id(tenant_id, current_user)
    return get_fee_structure(db, validated_id)


@fee_structure.put("/fee-structure/{tenant_id}", response_model=FeeStructureResponse)
def update_fee_structure_endpoint(
    fee_data: FeeStructureUpdate,
    tenant_id: int = Path(..., description="Tenant/School ID", gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
        UserRole.SECRETARY
    ))
):
    """
    Update fee structure settings (total amount and deadline)
    Admin, Super Admin, or Secretary only
    """
    validated_id = get_validated_tenant_id(tenant_id, current_user)
    return update_fee_structure(db, validated_id, fee_data)


# ============================================
# Installment Endpoints (with tenant_id in path)
# ============================================

@fee_structure.get("/fee-structure/{tenant_id}/installments", response_model=list[FeeInstallmentResponse])
def get_installments_endpoint(
    tenant_id: int = Path(..., description="Tenant/School ID", gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Get all active installments for a specific tenant/school
    """
    validated_id = get_validated_tenant_id(tenant_id, current_user)
    installments = get_installments(db, validated_id)
    return [FeeInstallmentResponse.from_installment(i) for i in installments]


@fee_structure.post("/fee-structure/{tenant_id}/installments", response_model=FeeInstallmentResponse, status_code=201)
def create_installment_endpoint(
    installment_data: FeeInstallmentCreate,
    tenant_id: int = Path(..., description="Tenant/School ID", gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
        UserRole.SECRETARY
    ))
):
    """
    Create a new fee installment for a specific tenant/school
    Admin, Super Admin, or Secretary only
    """
    validated_id = get_validated_tenant_id(tenant_id, current_user)
    installment = create_installment(db, validated_id, installment_data)
    return FeeInstallmentResponse.from_installment(installment)


@fee_structure.get("/fee-structure/{tenant_id}/installments/{installment_id}", response_model=FeeInstallmentResponse)
def get_installment_endpoint(
    tenant_id: int = Path(..., description="Tenant/School ID", gt=0),
    installment_id: int = Path(..., description="Installment ID", gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Get a specific installment by ID
    """
    validated_id = get_validated_tenant_id(tenant_id, current_user)
    installment = get_installment_by_id(db, installment_id, validated_id)
    return FeeInstallmentResponse.from_installment(installment)


@fee_structure.put("/fee-structure/{tenant_id}/installments/{installment_id}", response_model=FeeInstallmentResponse)
def update_installment_endpoint(
    installment_data: FeeInstallmentUpdate,
    tenant_id: int = Path(..., description="Tenant/School ID", gt=0),
    installment_id: int = Path(..., description="Installment ID", gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
        UserRole.SECRETARY
    ))
):
    """
    Update an existing fee installment
    Admin, Super Admin, or Secretary only
    """
    validated_id = get_validated_tenant_id(tenant_id, current_user)
    installment = update_installment(db, validated_id, installment_id, installment_data)
    return FeeInstallmentResponse.from_installment(installment)


@fee_structure.delete("/fee-structure/{tenant_id}/installments/{installment_id}", status_code=204)
def delete_installment_endpoint(
    tenant_id: int = Path(..., description="Tenant/School ID", gt=0),
    installment_id: int = Path(..., description="Installment ID", gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN
    ))
):
    """
    Delete a fee installment (soft delete - marks as inactive)
    Super Admin only
    """
    validated_id = get_validated_tenant_id(tenant_id, current_user)
    delete_installment(db, validated_id, installment_id)
    return None
