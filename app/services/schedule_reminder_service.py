"""
Service for sending schedule reminder emails
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.schedule import Schedule
from app.models.enrollment import Enrollment
from app.models.user import User
from app.models.course import Course
from app.models.schedule_reminder import ScheduleReminder
from app.models.tenant_settings import TenantSettings
from app.services.email_service import EmailService
from app.conf.config import settings

logger = logging.getLogger(__name__)


class ScheduleReminderService:
    """Service for managing schedule reminders"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_upcoming_classes(self, minutes_ahead: int = 30) -> List[Schedule]:
        """
        Get classes starting in the specified number of minutes
        
        Args:
            minutes_ahead: Number of minutes ahead to check (default: 30)
        
        Returns:
            List of Schedule objects
        """
        now = datetime.now()
        target_time = now + timedelta(minutes=minutes_ahead)
        
        # Get current day of week (0=Monday, 6=Sunday)
        current_day = now.weekday()
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        current_day_name = day_names[current_day]
        
        # Parse target time to HH:MM format
        target_time_str = target_time.strftime('%H:%M')
        
        # Query schedules for today with matching time
        # Filter out soft-deleted schedules
        query = self.db.query(Schedule).filter(
            and_(
                Schedule.day == current_day_name,
                Schedule.start_time == target_time_str,
                Schedule.deleted_at.is_(None)  # Exclude soft-deleted schedules
            )
        )
        
        schedules = query.all()
        return schedules
    
    def get_instructor_email(self, instructor_name: str, institution_id: Optional[int] = None) -> Optional[str]:
        """
        Get instructor email by name
        
        Args:
            instructor_name: Name of the instructor
            institution_id: Optional institution ID for tenant isolation
        
        Returns:
            Email address or None
        """
        # Try exact match first (full name)
        full_name_parts = instructor_name.strip().split()
        
        query = self.db.query(User).filter(
            and_(
                or_(
                    User.role == 'lecturer',
                    User.role == 'staff',
                    User.role == 'teacher',
                    User.role.like('%lecturer%'),
                    User.role.like('%staff%'),
                    User.role.like('%teacher%')
                ),
                User.deleted_at.is_(None),  # Exclude soft-deleted users
                User.is_active == 'active'  # Only active users
            )
        )
        
        # Try to match by full name or parts
        if len(full_name_parts) >= 2:
            # Try matching firstname and lastname
            name_conditions = or_(
                and_(
                    User.firstname.ilike(f"%{full_name_parts[0]}%"),
                    User.lastname.ilike(f"%{full_name_parts[-1]}%")
                ),
                User.username.ilike(f"%{instructor_name}%")
            )
        else:
            # Single name - try firstname, lastname, or username
            name_conditions = or_(
                User.firstname.ilike(f"%{instructor_name}%"),
                User.lastname.ilike(f"%{instructor_name}%"),
                User.username.ilike(f"%{instructor_name}%")
            )
        
        query = query.filter(name_conditions)
        
        if institution_id:
            query = query.filter(User.institution_id == institution_id)
        
        user = query.first()
        return user.email if user and user.email else None
    
    def get_student_emails_for_course(
        self,
        course_name: str,
        institution_id: Optional[int] = None
    ) -> List[str]:
        """
        Get all student emails enrolled in a course
        
        Args:
            course_name: Name of the course
            institution_id: Optional institution ID for tenant isolation
        
        Returns:
            List of student email addresses
        """
        # First, get the course ID by name
        course_query = self.db.query(Course).filter(
            and_(
                Course.name == course_name,
                Course.deleted_at.is_(None)  # Exclude soft-deleted courses
            )
        )
        if institution_id:
            course_query = course_query.filter(Course.institution_id == institution_id)
        
        course = course_query.first()
        if not course:
            logger.warning(f"Course not found: {course_name}")
            return []
        
        # Get all active enrollments for this course
        enrollment_query = self.db.query(Enrollment).filter(
            and_(
                Enrollment.course_id == course.id,
                Enrollment.status == 'active',
                Enrollment.deleted_at.is_(None)  # Exclude soft-deleted enrollments
            )
        )
        
        if institution_id:
            enrollment_query = enrollment_query.filter(Enrollment.institution_id == institution_id)
        
        enrollments = enrollment_query.all()
        
        # Get student IDs
        student_ids = [enrollment.student_id for enrollment in enrollments]
        
        if not student_ids:
            return []
        
        # Get student emails directly from Student table (students have email field)
        from app.models.student import Student
        students_query = self.db.query(Student).filter(
            and_(
                Student.id.in_(student_ids),
                Student.deleted_at.is_(None)  # Exclude soft-deleted students
            )
        )
        
        if institution_id:
            students_query = students_query.filter(Student.institution_id == institution_id)
        
        students = students_query.all()
        return [student.email for student in students if student.email]
    
    def has_reminder_been_sent(
        self,
        schedule_id: int,
        reminder_type: str,
        recipient_email: str,
        class_start_time: datetime,
        institution_id: int
    ) -> bool:
        """
        Check if a reminder has already been sent
        
        Args:
            schedule_id: Schedule ID
            reminder_type: 'instructor' or 'student'
            recipient_email: Email address
            class_start_time: When the class starts
            institution_id: Institution ID for tenant isolation
        
        Returns:
            True if reminder already sent
        """
        existing = self.db.query(ScheduleReminder).filter(
            and_(
                ScheduleReminder.schedule_id == schedule_id,
                ScheduleReminder.reminder_type == reminder_type,
                ScheduleReminder.recipient_email == recipient_email,
                ScheduleReminder.class_start_time == class_start_time,
                ScheduleReminder.institution_id == institution_id
            )
        ).first()
        
        return existing is not None
    
    def record_reminder_sent(
        self,
        schedule_id: int,
        institution_id: int,
        reminder_type: str,
        recipient_email: str,
        class_start_time: datetime,
        status: str = 'sent',
        error_message: Optional[str] = None
    ):
        """
        Record that a reminder was sent
        
        Args:
            schedule_id: Schedule ID
            institution_id: Institution ID
            reminder_type: 'instructor' or 'student'
            recipient_email: Email address
            class_start_time: When the class starts
            status: 'sent' or 'failed'
            error_message: Error message if failed
        """
        reminder = ScheduleReminder(
            schedule_id=schedule_id,
            institution_id=institution_id,
            reminder_type=reminder_type,
            recipient_email=recipient_email,
            reminder_time=datetime.now(),
            class_start_time=class_start_time,
            status=status,
            error_message=error_message
        )
        self.db.add(reminder)
        self.db.commit()
    
    def get_reminder_time(self, institution_id: Optional[int] = None) -> int:
        """
        Get the reminder time setting for an institution
        
        Args:
            institution_id: Institution ID to get settings for
        
        Returns:
            Minutes before class to send reminder (default: 30)
        """
        if not institution_id:
            return 30  # Default
        
        try:
            settings = self.db.query(TenantSettings).filter(
                TenantSettings.institution_id == institution_id
            ).first()
            
            if settings and settings.email_reminder_time is not None:
                return settings.email_reminder_time
        except Exception as e:
            logger.warning(f"Error fetching reminder time setting: {e}")
        
        return 30  # Default fallback
    
    async def send_reminders_for_upcoming_classes(self, minutes_ahead: Optional[int] = None):
        """
        Send reminder emails for classes starting in the specified minutes
        
        Args:
            minutes_ahead: Number of minutes ahead (if None, will use tenant setting)
        """
        # Get schedules grouped by institution_id to use different reminder times
        now = datetime.now()
        target_time = now + timedelta(minutes=minutes_ahead if minutes_ahead else 30)
        
        # Get current day of week
        current_day = now.weekday()
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        current_day_name = day_names[current_day]
        
        # Parse target time to HH:MM format
        target_time_str = target_time.strftime('%H:%M')
        
        # Query schedules for today with matching time
        query = self.db.query(Schedule).filter(
            and_(
                Schedule.day == current_day_name,
                Schedule.start_time == target_time_str,
                Schedule.deleted_at.is_(None)
            )
        )
        
        schedules = query.all()
        
        if not schedules:
            logger.info(f"No classes found starting at {target_time_str}")
            return
        
        logger.info(f"Found {len(schedules)} class(es) starting at {target_time_str}")
        
        # Group schedules by institution_id to use their specific reminder times
        schedules_by_institution = {}
        for schedule in schedules:
            inst_id = schedule.institution_id
            if inst_id not in schedules_by_institution:
                schedules_by_institution[inst_id] = []
            schedules_by_institution[inst_id].append(schedule)
        
        # Process each institution's schedules with their reminder time
        for institution_id, inst_schedules in schedules_by_institution.items():
            # Get reminder time for this institution
            reminder_time = self.get_reminder_time(institution_id)
            
            # Only process if this matches the current check time
            if minutes_ahead is None or minutes_ahead == reminder_time:
                for schedule in inst_schedules:
                    try:
                        # Calculate class start datetime
                        class_start_time = now + timedelta(minutes=reminder_time)
                        
                        # Send reminder to instructor
                        instructor_email = self.get_instructor_email(
                            schedule.instructor,
                            institution_id
                        )
                        
                        if instructor_email:
                            # Check if reminder already sent
                            if not self.has_reminder_been_sent(
                                schedule.id,
                                'instructor',
                                instructor_email,
                                class_start_time,
                                institution_id
                            ):
                                success = await EmailService.send_class_reminder_to_instructor(
                                    instructor_email=instructor_email,
                                    instructor_name=schedule.instructor,
                                    course_name=schedule.course_name,
                                    day=schedule.day,
                                    start_time=schedule.start_time,
                                    end_time=schedule.end_time,
                                    room=schedule.room or 'TBA'
                                )
                                
                                self.record_reminder_sent(
                                    schedule_id=schedule.id,
                                    institution_id=institution_id,
                                    reminder_type='instructor',
                                    recipient_email=instructor_email,
                                    class_start_time=class_start_time,
                                    status='sent' if success else 'failed',
                                    error_message=None if success else 'Email sending failed'
                                )
                                
                                if success:
                                    logger.info(f"Reminder sent to instructor: {instructor_email}")
                                else:
                                    logger.error(f"Failed to send reminder to instructor: {instructor_email}")
                            else:
                                logger.debug(f"Reminder already sent to instructor: {instructor_email}")
                        else:
                            logger.warning(f"Instructor email not found for: {schedule.instructor}")
                        
                        # Send reminders to students
                        student_emails = self.get_student_emails_for_course(
                            schedule.course_name,
                            institution_id
                        )
                        
                        if student_emails:
                            # Filter out students who already received reminder
                            emails_to_send = []
                            for email in student_emails:
                                if not self.has_reminder_been_sent(
                                    schedule.id,
                                    'student',
                                    email,
                                    class_start_time,
                                    institution_id
                                ):
                                    emails_to_send.append(email)
                            
                            if emails_to_send:
                                # Send bulk email to all students
                                success = await EmailService.send_class_reminder_to_students(
                                    student_emails=emails_to_send,
                                    course_name=schedule.course_name,
                                    day=schedule.day,
                                    start_time=schedule.start_time,
                                    end_time=schedule.end_time,
                                    room=schedule.room or 'TBA',
                                    instructor_name=schedule.instructor
                                )
                                
                                # Record reminders for each student
                                for email in emails_to_send:
                                    self.record_reminder_sent(
                                        schedule_id=schedule.id,
                                        institution_id=institution_id,
                                        reminder_type='student',
                                        recipient_email=email,
                                        class_start_time=class_start_time,
                                        status='sent' if success else 'failed',
                                        error_message=None if success else 'Email sending failed'
                                    )
                                
                                if success:
                                    logger.info(f"Reminders sent to {len(emails_to_send)} student(s)")
                                else:
                                    logger.error(f"Failed to send reminders to students")
                            else:
                                logger.debug("All students already received reminders")
                        else:
                            logger.warning(f"No enrolled students found for course: {schedule.course_name}")
                            
                    except Exception as e:
                        logger.error(f"Error processing reminder for schedule {schedule.id}: {str(e)}")
                        continue
