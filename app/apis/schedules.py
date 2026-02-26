from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.schedule import Schedule
from app.models.user import User
from app.models.course import Course
from app.models.teacher import Teacher
from app.schemas.schedules import ScheduleRequest, ScheduleUpdate, ScheduleResponse, CourseInfo, InstructorInfo
from app.exceptions import NotFoundError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity, log_delete_activity
from datetime import datetime

def create_schedule(db: Session, schedule: ScheduleRequest, current_user: Optional[User] = None) -> Schedule:
    """Create a new schedule"""
    # Determine institution_id
    institution_id = schedule.institution_id
    if not institution_id and current_user:
        institution_id = current_user.institution_id
    
    if not institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the request body or ensure the user belongs to an institution")
    
    # Create schedule with institution_id
    schedule_dict = schedule.dict(exclude={'institution_id'})
    schedule_dict['institution_id'] = institution_id
    new_schedule = Schedule(**schedule_dict)
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    
    # Log activity if current_user is provided
    if current_user:
        try:
            schedule_name = f"{schedule.course_name} - {schedule.day} {schedule.start_time}-{schedule.end_time}"
            log_create_activity(
                db=db,
                current_user=current_user,
                entity_type="schedule",
                entity_id=new_schedule.id,
                entity_name=schedule_name,
                institution_id=institution_id,
                content=f"Created schedule: {schedule_name}"
            )
        except Exception as e:
            print(f"Error logging schedule creation activity: {e}")
    
    return new_schedule

def _enrich_schedule_data(db: Session, schedule: Schedule) -> Dict[str, Any]:
    """Enrich schedule data with course and instructor information"""
    course_info = None
    instructor_info = None
    
    # Look up course by name
    if schedule.course_name:
        course = db.query(Course).filter(
            Course.name == schedule.course_name,
            Course.institution_id == schedule.institution_id,
            Course.deleted_at.is_(None)
        ).first()
        if course:
            course_info = CourseInfo(
                id=course.id,
                name=course.name,
                code=course.code,
                description=course.description
            )
    
    # Look up instructor/teacher by name or email
    if schedule.instructor:
        # Try to find by full name (firstname + lastname)
        instructor_parts = schedule.instructor.split()
        teacher = None
        
        if len(instructor_parts) >= 2:
            # Try matching by firstname and lastname
            teacher = db.query(Teacher).filter(
                Teacher.firstname.ilike(f"%{instructor_parts[0]}%"),
                Teacher.lastname.ilike(f"%{instructor_parts[-1]}%"),
                Teacher.institution_id == schedule.institution_id,
                Teacher.deleted_at.is_(None)
            ).first()
        
        if not teacher:
            # Try matching by email if instructor string looks like an email
            if "@" in schedule.instructor:
                teacher = db.query(Teacher).filter(
                    Teacher.email == schedule.instructor,
                    Teacher.institution_id == schedule.institution_id,
                    Teacher.deleted_at.is_(None)
                ).first()
        
        if not teacher:
            # Try matching by employee_id
            teacher = db.query(Teacher).filter(
                Teacher.employee_id == schedule.instructor,
                Teacher.institution_id == schedule.institution_id,
                Teacher.deleted_at.is_(None)
            ).first()
        
        if teacher:
            instructor_info = InstructorInfo(
                id=teacher.id,
                name=f"{teacher.firstname} {teacher.lastname}".strip(),
                email=teacher.email,
                employee_id=teacher.employee_id
            )
    
    return {
        "course_info": course_info,
        "instructor_info": instructor_info
    }

def get_schedule(db: Session, schedule_id: int) -> Schedule:
    """Get a schedule by ID"""
    schedule = db.query(Schedule).filter(
        Schedule.id == schedule_id,
        Schedule.deleted_at.is_(None)
    ).first()
    if not schedule:
        raise NotFoundError(f"Schedule with ID {schedule_id} not found")
    return schedule

def get_schedule_with_enriched_data(db: Session, schedule_id: int) -> ScheduleResponse:
    """Get a schedule by ID with enriched course and instructor data"""
    schedule = get_schedule(db, schedule_id)
    enriched_data = _enrich_schedule_data(db, schedule)
    
    # Create ScheduleResponse with enriched data
    return ScheduleResponse(
        id=schedule.id,
        institution_id=schedule.institution_id,
        course_name=schedule.course_name,
        instructor=schedule.instructor,
        day=schedule.day,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        room=schedule.room,
        capacity=schedule.capacity,
        description=schedule.description,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
        course_info=enriched_data.get("course_info"),
        instructor_info=enriched_data.get("instructor_info")
    )

def get_schedules(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    institution_id: Optional[int] = None,
    instructor: Optional[str] = None,
    day: Optional[str] = None,
    course_name: Optional[str] = None
) -> tuple[List[Schedule], int]:
    """Get list of schedules with pagination"""
    query = db.query(Schedule).filter(Schedule.deleted_at.is_(None))
    
    # Filter by institution_id for tenant isolation
    if institution_id is not None:
        query = query.filter(Schedule.institution_id == institution_id)
    
    if instructor:
        query = query.filter(Schedule.instructor.ilike(f"%{instructor}%"))
    
    if day:
        query = query.filter(Schedule.day == day)
    
    if course_name:
        query = query.filter(Schedule.course_name.ilike(f"%{course_name}%"))
    
    return paginate_query(query, page=(skip // limit) + 1, page_size=limit)

def get_schedules_with_enriched_data(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    institution_id: Optional[int] = None,
    instructor: Optional[str] = None,
    day: Optional[str] = None,
    course_name: Optional[str] = None
) -> tuple[List[ScheduleResponse], int]:
    """Get list of schedules with enriched course and instructor data"""
    schedules, total = get_schedules(
        db=db,
        skip=skip,
        limit=limit,
        institution_id=institution_id,
        instructor=instructor,
        day=day,
        course_name=course_name
    )
    
    # Enrich each schedule with course and instructor info
    enriched_schedules = []
    for schedule in schedules:
        enriched_data = _enrich_schedule_data(db, schedule)
        schedule_response = ScheduleResponse(
            id=schedule.id,
            institution_id=schedule.institution_id,
            course_name=schedule.course_name,
            instructor=schedule.instructor,
            day=schedule.day,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            room=schedule.room,
            capacity=schedule.capacity,
            description=schedule.description,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
            course_info=enriched_data.get("course_info"),
            instructor_info=enriched_data.get("instructor_info")
        )
        enriched_schedules.append(schedule_response)
    
    return enriched_schedules, total

def update_schedule(db: Session, schedule_id: int, schedule_update: ScheduleUpdate, current_user: Optional[User] = None) -> Schedule:
    """Update a schedule"""
    schedule = get_schedule(db, schedule_id)
    
    update_data = schedule_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)
    
    db.commit()
    db.refresh(schedule)
    
    # Log activity if current_user is provided
    if current_user:
        try:
            schedule_name = f"{schedule.course_name} - {schedule.day} {schedule.start_time}-{schedule.end_time}"
            log_update_activity(
                db=db,
                current_user=current_user,
                entity_type="schedule",
                entity_id=schedule.id,
                entity_name=schedule_name,
                institution_id=schedule.institution_id,
                content=f"Updated schedule: {schedule_name}"
            )
        except Exception as e:
            print(f"Error logging schedule update activity: {e}")
    
    return schedule

def delete_schedule(db: Session, schedule_id: int, current_user: Optional[User] = None) -> bool:
    """Soft delete a schedule"""
    schedule = get_schedule(db, schedule_id)
    schedule_name = f"{schedule.course_name} - {schedule.day} {schedule.start_time}-{schedule.end_time}"
    institution_id = schedule.institution_id
    schedule.deleted_at = datetime.utcnow()
    db.commit()
    
    # Log activity if current_user is provided
    if current_user:
        try:
            log_delete_activity(
                db=db,
                current_user=current_user,
                entity_type="schedule",
                entity_id=schedule_id,
                entity_name=schedule_name,
                institution_id=institution_id,
                content=f"Deleted schedule: {schedule_name}"
            )
        except Exception as e:
            print(f"Error logging schedule deletion activity: {e}")
    
    return True

def get_schedules_by_instructor(db: Session, instructor: str, institution_id: Optional[int] = None) -> List[Schedule]:
    """Get all schedules for a specific instructor"""
    query = db.query(Schedule).filter(
        Schedule.instructor == instructor,
        Schedule.deleted_at.is_(None)
    )
    
    # Filter by institution_id for tenant isolation
    if institution_id is not None:
        query = query.filter(Schedule.institution_id == institution_id)
    
    return query.all()

def get_schedules_by_instructor_with_enriched_data(db: Session, instructor: str, institution_id: Optional[int] = None) -> List[ScheduleResponse]:
    """Get all schedules for a specific instructor with enriched data"""
    schedules = get_schedules_by_instructor(db, instructor, institution_id)
    
    # Enrich each schedule with course and instructor info
    enriched_schedules = []
    for schedule in schedules:
        enriched_data = _enrich_schedule_data(db, schedule)
        schedule_response = ScheduleResponse(
            id=schedule.id,
            institution_id=schedule.institution_id,
            course_name=schedule.course_name,
            instructor=schedule.instructor,
            day=schedule.day,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            room=schedule.room,
            capacity=schedule.capacity,
            description=schedule.description,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
            course_info=enriched_data.get("course_info"),
            instructor_info=enriched_data.get("instructor_info")
        )
        enriched_schedules.append(schedule_response)
    
    return enriched_schedules
