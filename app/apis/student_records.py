from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from app.models.student_record import StudentRecord
from app.models.user import User
from app.schemas.student_records import StudentRecordRequest, StudentRecordUpdate
from app.exceptions import NotFoundError, ValidationError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity, log_delete_activity
from datetime import datetime

def calculate_grade_and_gpa(total_score: Decimal) -> tuple[str, Decimal]:
    """Calculate letter grade and GPA from total score"""
    if total_score >= 90:
        return 'A', Decimal('4.0')
    elif total_score >= 80:
        return 'B', Decimal('3.0')
    elif total_score >= 70:
        return 'C', Decimal('2.0')
    elif total_score >= 60:
        return 'D', Decimal('1.0')
    else:
        return 'F', Decimal('0.0')

def create_student_record(db: Session, record: StudentRecordRequest, current_user: Optional[User] = None) -> StudentRecord:
    """Create a new student record"""
    # Validate CA + Assignment doesn't exceed 30
    assignment = record.assignment or Decimal('0')
    ca = record.ca or Decimal('0')
    ca_assignment_total = assignment + ca
    
    if ca_assignment_total > 30:
        raise ValidationError(f"Assignment and CA combined cannot exceed 30. Current total: {ca_assignment_total}")
    
    # Calculate total score
    exam = record.exam or Decimal('0')
    total_score = ca_assignment_total + exam
    
    # Calculate grade and GPA
    letter_grade, gpa = calculate_grade_and_gpa(total_score)
    
    new_record = StudentRecord(
        student_id=record.student_id,
        course_code=record.course_code,
        semester=record.semester,
        assignment=assignment,
        ca=ca,
        exam=exam,
        total_score=total_score,
        letter_grade=letter_grade,
        gpa=gpa
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    # Log activity if current_user is provided
    if current_user:
        try:
            record_name = f"Record for {record.student_id} - {record.course_code} ({record.semester})"
            institution_id = getattr(new_record, 'institution_id', None) or (current_user.institution_id if current_user else None)
            if institution_id:
                log_create_activity(
                    db=db,
                    current_user=current_user,
                    entity_type="student_record",
                    entity_id=new_record.id,
                    entity_name=record_name,
                    institution_id=institution_id,
                    content=f"Created student record: {record_name}"
                )
        except Exception as e:
            print(f"Error logging student record creation activity: {e}")
    
    return new_record

def get_student_record(db: Session, record_id: int) -> StudentRecord:
    """Get a student record by ID"""
    record = db.query(StudentRecord).filter(
        StudentRecord.id == record_id,
        StudentRecord.deleted_at.is_(None)
    ).first()
    if not record:
        raise NotFoundError(f"Student record with ID {record_id} not found")
    return record

def get_student_records(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    student_id: Optional[str] = None,
    course_code: Optional[str] = None,
    semester: Optional[str] = None,
    letter_grade: Optional[str] = None
) -> tuple[List[StudentRecord], int]:
    """Get list of student records with pagination"""
    query = db.query(StudentRecord).filter(StudentRecord.deleted_at.is_(None))
    
    if student_id:
        query = query.filter(StudentRecord.student_id.ilike(f"%{student_id}%"))
    
    if course_code:
        query = query.filter(StudentRecord.course_code.ilike(f"%{course_code}%"))
    
    if semester:
        query = query.filter(StudentRecord.semester == semester)
    
    if letter_grade:
        query = query.filter(StudentRecord.letter_grade == letter_grade)
    
    return paginate_query(query, page=(skip // limit) + 1, page_size=limit)

def update_student_record(db: Session, record_id: int, record_update: StudentRecordUpdate, current_user: Optional[User] = None) -> StudentRecord:
    """Update a student record"""
    record = get_student_record(db, record_id)
    
    update_data = record_update.dict(exclude_unset=True)
    
    # If assignment or CA is being updated, validate the sum
    assignment = Decimal(str(update_data.get('assignment', record.assignment) or 0))
    ca = Decimal(str(update_data.get('ca', record.ca) or 0))
    ca_assignment_total = assignment + ca
    
    if ca_assignment_total > 30:
        raise ValidationError(f"Assignment and CA combined cannot exceed 30. Current total: {ca_assignment_total}")
    
    # Update fields
    for field, value in update_data.items():
        setattr(record, field, value)
    
    # Recalculate total, grade, and GPA
    exam = Decimal(str(record.exam or 0))
    total_score = ca_assignment_total + exam
    letter_grade, gpa = calculate_grade_and_gpa(total_score)
    
    record.total_score = total_score
    record.letter_grade = letter_grade
    record.gpa = gpa
    
    db.commit()
    db.refresh(record)
    
    # Log activity if current_user is provided
    if current_user:
        try:
            record_name = f"Record for {record.student_id} - {record.course_code} ({record.semester})"
            institution_id = getattr(record, 'institution_id', None) or (current_user.institution_id if current_user else None)
            if institution_id:
                log_update_activity(
                    db=db,
                    current_user=current_user,
                    entity_type="student_record",
                    entity_id=record.id,
                    entity_name=record_name,
                    institution_id=institution_id,
                    content=f"Updated student record: {record_name}"
                )
        except Exception as e:
            print(f"Error logging student record update activity: {e}")
    
    return record

def delete_student_record(db: Session, record_id: int, current_user: Optional[User] = None) -> bool:
    """Soft delete a student record"""
    record = get_student_record(db, record_id)
    record_name = f"Record for {record.student_id} - {record.course_code} ({record.semester})"
    institution_id = getattr(record, 'institution_id', None) or (current_user.institution_id if current_user else None)
    record.deleted_at = datetime.utcnow()
    db.commit()
    
    # Log activity if current_user is provided
    if current_user and institution_id:
        try:
            log_delete_activity(
                db=db,
                current_user=current_user,
                entity_type="student_record",
                entity_id=record_id,
                entity_name=record_name,
                institution_id=institution_id,
                content=f"Deleted student record: {record_name}"
            )
        except Exception as e:
            print(f"Error logging student record deletion activity: {e}")
    
    return True
