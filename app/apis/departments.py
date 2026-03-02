from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.department import Department
from app.models.user import User
from app.schemas.departments import DepartmentRequest, DepartmentResponse, DepartmentUpdate
from app.exceptions import NotFoundError, ConflictError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity, log_delete_activity


def create_department(db: Session, department: DepartmentRequest, institution_id: Optional[int] = None, current_user: Optional[User] = None) -> Department:
    """Create a new department"""
    # Use institution_id from request if provided, otherwise use the parameter
    final_institution_id = department.institution_id or institution_id
    
    if not final_institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the request body or pass it as a parameter")
    
    # Check if department code already exists for this institution
    existing = db.query(Department).filter(
        Department.code == department.code,
        Department.institution_id == final_institution_id,
        Department.deleted_at.is_(None)
    ).first()
    if existing:
        raise ConflictError(f"Department with code {department.code} already exists for this institution")
    
    # Create department with institution_id
    department_dict = department.dict(exclude={'institution_id'})
    department_dict['institution_id'] = final_institution_id
    new_department = Department(**department_dict)
    db.add(new_department)
    db.commit()
    db.refresh(new_department)
    
    # Log activity if current_user is provided
    if current_user:
        try:
            department_name = f"{department.code} - {department.name}"
            log_create_activity(
                db=db,
                current_user=current_user,
                entity_type="department",
                entity_id=new_department.id,
                entity_name=department_name,
                institution_id=final_institution_id,
                content=f"Created department: {department_name}"
            )
        except Exception as e:
            print(f"Error logging department creation activity: {e}")
    
    return new_department


def get_department(db: Session, department_id: int) -> Department:
    """Get a department by ID"""
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.deleted_at.is_(None)
    ).first()
    if not department:
        raise NotFoundError(f"Department with ID {department_id} not found")
    return department


def get_departments(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    institution_id: Optional[int] = None
) -> tuple[List[Department], int]:
    """Get list of departments with pagination"""
    query = db.query(Department).filter(Department.deleted_at.is_(None))
    
    # Filter by institution_id if provided (required for multi-tenancy)
    # If institution_id is None, this might be a system admin viewing all departments
    # For tenant users, institution_id should always be provided
    if institution_id is not None:
        query = query.filter(Department.institution_id == institution_id)
    
    return paginate_query(query, page=(skip // limit) + 1, page_size=limit)


def update_department(db: Session, department_id: int, department_update: DepartmentUpdate, current_user: Optional[User] = None) -> Department:
    """Update a department"""
    department = get_department(db, department_id)
    
    update_data = department_update.dict(exclude_unset=True)
    
    # Check code uniqueness if being updated
    if "code" in update_data:
        existing = db.query(Department).filter(
            Department.code == update_data["code"],
            Department.institution_id == department.institution_id,
            Department.id != department_id,
            Department.deleted_at.is_(None)
        ).first()
        if existing:
            raise ConflictError(f"Department with code {update_data['code']} already exists for this institution")
    
    for field, value in update_data.items():
        setattr(department, field, value)
    
    db.commit()
    db.refresh(department)
    
    # Log activity if current_user is provided
    if current_user:
        try:
            department_name = f"{department.code} - {department.name}"
            log_update_activity(
                db=db,
                current_user=current_user,
                entity_type="department",
                entity_id=department_id,
                entity_name=department_name,
                institution_id=department.institution_id,
                content=f"Updated department: {department_name}"
            )
        except Exception as e:
            print(f"Error logging department update activity: {e}")
    
    return department


def delete_department(db: Session, department_id: int, current_user: Optional[User] = None) -> bool:
    """Soft delete a department"""
    department = get_department(db, department_id)
    department_name = f"{department.code} - {department.name}"
    institution_id = department.institution_id
    
    from datetime import datetime
    department.deleted_at = datetime.utcnow()
    db.commit()
    
    # Log activity if current_user is provided
    if current_user:
        try:
            log_delete_activity(
                db=db,
                current_user=current_user,
                entity_type="department",
                entity_id=department_id,
                entity_name=department_name,
                institution_id=institution_id,
                content=f"Deleted department: {department_name}"
            )
        except Exception as e:
            print(f"Error logging department deletion activity: {e}")
    
    return True
