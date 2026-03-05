"""
API routes for schedule reminders
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, List
from datetime import datetime, timedelta

from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.models.schedule_reminder import ScheduleReminder
from app.models.schedule import Schedule
from app.models.enrollment import Enrollment
from app.models.course import Course
from app.schemas.reminders import ReminderStatusResponse, UserReminderResponse, DismissReminderRequest
from app.helpers.pagination import PaginatedResponse

reminder_router = APIRouter()


@reminder_router.get("/reminders/status", response_model=PaginatedResponse[ReminderStatusResponse])
def get_reminder_status(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    institution_id: Optional[int] = Query(None, alias="institution_id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """
    Get reminder status for admin dashboard
    Shows which reminders have been sent and to whom
    """
    # Build query for schedules
    query = db.query(Schedule).filter(Schedule.deleted_at.is_(None))
    
    if institution_id:
        query = query.filter(Schedule.institution_id == institution_id)
    elif current_user.institution_id:
        query = query.filter(Schedule.institution_id == current_user.institution_id)
    
    # Get total count
    total = query.count()
    
    # Paginate
    schedules = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # Build response with reminder status
    items = []
    for schedule in schedules:
        # Get instructor reminder status
        instructor_reminder = db.query(ScheduleReminder).filter(
            and_(
                ScheduleReminder.schedule_id == schedule.id,
                ScheduleReminder.reminder_type == 'instructor',
                ScheduleReminder.institution_id == schedule.institution_id
            )
        ).first()
        
        # Get student reminder count
        student_reminders = db.query(ScheduleReminder).filter(
            and_(
                ScheduleReminder.schedule_id == schedule.id,
                ScheduleReminder.reminder_type == 'student',
                ScheduleReminder.status == 'sent',
                ScheduleReminder.institution_id == schedule.institution_id
            )
        ).count()
        
        # Get total enrolled students
        course = db.query(Course).filter(
            and_(
                Course.name == schedule.course_name,
                Course.institution_id == schedule.institution_id,
                Course.deleted_at.is_(None)
            )
        ).first()
        
        total_students = 0
        if course:
            total_students = db.query(Enrollment).filter(
                and_(
                    Enrollment.course_id == course.id,
                    Enrollment.status == 'active',
                    Enrollment.institution_id == schedule.institution_id,
                    Enrollment.deleted_at.is_(None)
                )
            ).count()
        
        # Calculate class start datetime
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        schedule_day_index = day_names.index(schedule.day) if schedule.day in day_names else 0
        today_index = datetime.now().weekday()
        days_until = (schedule_day_index - today_index) % 7
        if days_until == 0 and datetime.now().strftime('%H:%M') >= schedule.start_time:
            days_until = 7
        
        class_start_date = datetime.now().date() + timedelta(days=days_until)
        class_start_time = datetime.combine(class_start_date, datetime.strptime(schedule.start_time, '%H:%M').time())
        
        items.append(ReminderStatusResponse(
            schedule_id=schedule.id,
            course_name=schedule.course_name,
            instructor=schedule.instructor,
            day=schedule.day,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            room=schedule.room,
            class_start_time=class_start_time,
            instructor_reminder_sent=instructor_reminder is not None,
            instructor_email=instructor_reminder.recipient_email if instructor_reminder else None,
            student_reminders_sent=student_reminders,
            total_enrolled_students=total_students,
            reminder_sent_at=instructor_reminder.sent_at if instructor_reminder else None
        ))
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@reminder_router.get("/reminders/my", response_model=List[UserReminderResponse])
def get_my_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Get reminders for current user (lecturer or student)
    """
    user_email = current_user.email
    
    # Get reminders for this user
    reminders = db.query(ScheduleReminder).filter(
        and_(
            ScheduleReminder.recipient_email == user_email,
            ScheduleReminder.status == 'sent',
            ScheduleReminder.class_start_time >= datetime.now(),  # Only future classes
            ScheduleReminder.institution_id == current_user.institution_id
        )
    ).order_by(ScheduleReminder.class_start_time.asc()).all()
    
    # Get dismissed reminder IDs
    from app.models.user_reminder_dismissal import UserReminderDismissal
    dismissed_ids = db.query(UserReminderDismissal.reminder_id).filter(
        UserReminderDismissal.user_id == current_user.id
    ).all()
    dismissed_ids_set = {r[0] for r in dismissed_ids}
    
    # Build response with schedule details
    items = []
    for reminder_obj in reminders:
        schedule = db.query(Schedule).filter(
            and_(
                Schedule.id == reminder_obj.schedule_id,
                Schedule.deleted_at.is_(None)
            )
        ).first()
        if not schedule:
            continue
        
        items.append(UserReminderResponse(
            id=reminder_obj.id,
            schedule_id=reminder_obj.schedule_id,
            course_name=schedule.course_name,
            instructor=schedule.instructor,
            day=schedule.day,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            room=schedule.room,
            class_start_time=reminder_obj.class_start_time,
            reminder_time=reminder_obj.reminder_time,
            is_dismissed=reminder_obj.id in dismissed_ids_set
        ))
    
    return items


@reminder_router.post("/reminders/dismiss")
def dismiss_reminder(
    request: DismissReminderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Dismiss a reminder so it doesn't show for the user anymore
    """
    from app.models.user_reminder_dismissal import UserReminderDismissal
    
    # Check if reminder exists and belongs to user
    reminder_obj = db.query(ScheduleReminder).filter(
        and_(
            ScheduleReminder.id == request.reminder_id,
            ScheduleReminder.recipient_email == current_user.email,
            ScheduleReminder.institution_id == current_user.institution_id
        )
    ).first()
    
    if not reminder_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found"
        )
    
    # Check if already dismissed
    existing = db.query(UserReminderDismissal).filter(
        and_(
            UserReminderDismissal.user_id == current_user.id,
            UserReminderDismissal.reminder_id == request.reminder_id
        )
    ).first()
    
    if existing:
        return {"message": "Reminder already dismissed", "dismissed": True}
    
    # Create dismissal record
    dismissal = UserReminderDismissal(
        user_id=current_user.id,
        reminder_id=request.reminder_id
    )
    db.add(dismissal)
    db.commit()
    
    return {"message": "Reminder dismissed successfully", "dismissed": True}
