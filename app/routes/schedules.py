from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.schedules import ScheduleRequest, ScheduleResponse, ScheduleUpdate
from app.apis.schedules import (
    create_schedule, get_schedule, get_schedules,
    update_schedule, delete_schedule, get_schedules_by_instructor,
    get_schedule_with_enriched_data, get_schedules_with_enriched_data,
    get_schedules_by_instructor_with_enriched_data
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

schedule = APIRouter()

@schedule.post("/schedules", response_model=ScheduleResponse, status_code=201)
def create_schedule_endpoint(
    schedule_data: ScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    """Create a new schedule"""
    new_schedule = create_schedule(db=db, schedule=schedule_data, current_user=current_user)
    # Return enriched data
    return get_schedule_with_enriched_data(db=db, schedule_id=new_schedule.id)

@schedule.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
def get_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a schedule by ID with enriched course and instructor information"""
    return get_schedule_with_enriched_data(db=db, schedule_id=schedule_id)

@schedule.get("/schedules")
def list_schedules(
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    instructor: Optional[str] = Query(None),
    day: Optional[str] = Query(None),
    course_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of schedules with optional pagination and enriched course/instructor information.
    If page and page_size are not provided, returns all schedules as a list."""
    # Determine institution_id for filtering
    institution_id = None
    if current_user:
        is_system_admin = current_user.role and current_user.role.startswith('system_')
        if not is_system_admin:
            institution_id = current_user.institution_id
            if not institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view schedules")
    
    # If pagination parameters are not provided, return all schedules
    if page is None or page_size is None:
        schedules, _ = get_schedules_with_enriched_data(
            db=db,
            skip=0,
            limit=1000000,  # Large limit to get all schedules
            institution_id=institution_id,
            instructor=instructor,
            day=day,
            course_name=course_name
        )
        return schedules  # Return as list when no pagination
    
    # Use pagination
    skip = (page - 1) * page_size
    schedules, total = get_schedules_with_enriched_data(
        db=db,
        skip=skip,
        limit=page_size,
        institution_id=institution_id,
        instructor=instructor,
        day=day,
        course_name=course_name
    )
    return PaginatedResponse.create(
        items=schedules,
        total=total,
        page=page,
        page_size=page_size
    )

@schedule.get("/schedules/instructor/{instructor_name}", response_model=list[ScheduleResponse])
def get_instructor_schedules(
    instructor_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get all schedules for a specific instructor with enriched course/instructor information"""
    # Determine institution_id for filtering
    institution_id = None
    if current_user:
        is_system_admin = current_user.role and current_user.role.startswith('system_')
        if not is_system_admin:
            institution_id = current_user.institution_id
            if not institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view schedules")
    
    return get_schedules_by_instructor_with_enriched_data(db=db, instructor=instructor_name, institution_id=institution_id)

@schedule.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
def update_schedule_endpoint(
    schedule_id: int,
    schedule_update: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    """Update a schedule"""
    updated_schedule = update_schedule(db=db, schedule_id=schedule_id, schedule_update=schedule_update, current_user=current_user)
    # Return enriched data
    return get_schedule_with_enriched_data(db=db, schedule_id=updated_schedule.id)

@schedule.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    """Delete a schedule (soft delete)"""
    delete_schedule(db=db, schedule_id=schedule_id, current_user=current_user)
    return None
