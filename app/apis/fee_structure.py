"""
Fee Structure API - CRUD operations for fee structure and installments
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from app.models.fee_structure import FeeStructure, FeeInstallment
from app.schemas.fee_structure import (
    FeeStructureUpdate,
    FeeInstallmentCreate,
    FeeInstallmentUpdate,
    FeeInstallmentResponse
)
from app.exceptions import NotFoundError, ValidationError


def get_or_create_fee_structure(
    db: Session,
    tenant_id: int
) -> FeeStructure:
    """Get existing fee structure or create a new one for the tenant"""
    fee_structure = db.query(FeeStructure).filter(
        FeeStructure.tenant_id == tenant_id
    ).first()
    
    if not fee_structure:
        fee_structure = FeeStructure(
            tenant_id=tenant_id,
            fee_amount=Decimal('0'),
            fee_deadline=None
        )
        db.add(fee_structure)
        db.commit()
        db.refresh(fee_structure)
    
    return fee_structure


def get_fee_structure(
    db: Session,
    tenant_id: int
) -> FeeStructure:
    """Get fee structure for a tenant"""
    fee_structure = db.query(FeeStructure).filter(
        FeeStructure.tenant_id == tenant_id
    ).first()
    
    if not fee_structure:
        # Return a mock structure if none exists
        return FeeStructure(
            id=0,
            tenant_id=tenant_id,
            fee_amount=Decimal('0'),
            fee_deadline=None
        )
    
    return fee_structure


def update_fee_structure(
    db: Session,
    tenant_id: int,
    fee_data: FeeStructureUpdate
) -> FeeStructure:
    """Update fee structure settings"""
    fee_structure = get_or_create_fee_structure(db, tenant_id)
    
    if fee_data.fee_amount is not None:
        fee_structure.fee_amount = fee_data.fee_amount
    
    if fee_data.fee_deadline is not None:
        try:
            fee_structure.fee_deadline = datetime.fromisoformat(fee_data.fee_deadline.replace('Z', '+00:00'))
        except ValueError:
            try:
                fee_structure.fee_deadline = datetime.strptime(fee_data.fee_deadline, '%Y-%m-%d')
            except ValueError:
                raise ValidationError("Invalid fee_deadline format. Use YYYY-MM-DD or ISO format.")
    
    if fee_data.academic_year is not None:
        fee_structure.academic_year = fee_data.academic_year
    
    db.commit()
    db.refresh(fee_structure)
    return fee_structure


def get_installments(
    db: Session,
    tenant_id: int
) -> List[FeeInstallment]:
    """Get all active installments for a tenant"""
    installments = db.query(FeeInstallment).filter(
        FeeInstallment.tenant_id == tenant_id,
        FeeInstallment.is_active == 1
    ).order_by(FeeInstallment.order_index.asc().nullslast(), FeeInstallment.due_date.asc()).all()
    
    return installments


def get_all_installments(
    db: Session,
    tenant_id: int,
    include_inactive: bool = False
) -> List[FeeInstallment]:
    """Get all installments including inactive ones"""
    query = db.query(FeeInstallment).filter(
        FeeInstallment.tenant_id == tenant_id
    )
    
    if not include_inactive:
        query = query.filter(FeeInstallment.is_active == 1)
    
    return query.order_by(FeeInstallment.order_index.asc().nullslast(), FeeInstallment.due_date.asc()).all()


def get_installment_by_id(
    db: Session,
    installment_id: int,
    tenant_id: int
) -> FeeInstallment:
    """Get a specific installment by ID"""
    installment = db.query(FeeInstallment).filter(
        FeeInstallment.id == installment_id,
        FeeInstallment.tenant_id == tenant_id
    ).first()
    
    if not installment:
        raise NotFoundError(f"Installment with ID {installment_id} not found")
    
    return installment


def create_installment(
    db: Session,
    tenant_id: int,
    installment_data: FeeInstallmentCreate
) -> FeeInstallment:
    """Create a new fee installment"""
    # Parse due date
    try:
        due_date = datetime.fromisoformat(installment_data.due_date.replace('Z', '+00:00'))
    except ValueError:
        try:
            due_date = datetime.strptime(installment_data.due_date, '%Y-%m-%d')
        except ValueError:
            raise ValidationError("Invalid due_date format. Use YYYY-MM-DD or ISO format.")
    
    # Get next order index if not provided
    order_index = installment_data.order_index
    if order_index is None:
        last_installment = db.query(FeeInstallment).filter(
            FeeInstallment.tenant_id == tenant_id
        ).order_by(FeeInstallment.order_index.desc().nullslast()).first()
        
        if last_installment and last_installment.order_index is not None:
            order_index = last_installment.order_index + 1
        else:
            order_index = 0
    
    installment = FeeInstallment(
        tenant_id=tenant_id,
        name=installment_data.name,
        amount=installment_data.amount,
        due_date=due_date,
        order_index=order_index,
        is_active=1
    )
    
    db.add(installment)
    db.commit()
    db.refresh(installment)
    
    return installment


def update_installment(
    db: Session,
    tenant_id: int,
    installment_id: int,
    installment_data: FeeInstallmentUpdate
) -> FeeInstallment:
    """Update an existing fee installment"""
    installment = get_installment_by_id(db, installment_id, tenant_id)
    
    if installment_data.name is not None:
        installment.name = installment_data.name
    
    if installment_data.amount is not None:
        installment.amount = installment_data.amount
    
    if installment_data.due_date is not None:
        try:
            installment.due_date = datetime.fromisoformat(installment_data.due_date.replace('Z', '+00:00'))
        except ValueError:
            try:
                installment.due_date = datetime.strptime(installment_data.due_date, '%Y-%m-%d')
            except ValueError:
                raise ValidationError("Invalid due_date format. Use YYYY-MM-DD or ISO format.")
    
    if installment_data.order_index is not None:
        installment.order_index = installment_data.order_index
    
    if installment_data.is_active is not None:
        installment.is_active = installment_data.is_active
    
    db.commit()
    db.refresh(installment)
    
    return installment


def delete_installment(
    db: Session,
    tenant_id: int,
    installment_id: int
) -> bool:
    """Soft delete a fee installment by marking it inactive"""
    installment = get_installment_by_id(db, installment_id, tenant_id)
    installment.is_active = 0
    db.commit()
    return True


def permanently_delete_installment(
    db: Session,
    tenant_id: int,
    installment_id: int
) -> bool:
    """Permanently delete a fee installment"""
    installment = get_installment_by_id(db, installment_id, tenant_id)
    db.delete(installment)
    db.commit()
    return True
