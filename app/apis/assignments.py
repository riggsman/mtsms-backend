from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.assignment import Assignment, AssignmentSubmission
from app.schemas.assignments import (
    AssignmentRequest, AssignmentUpdate,
    AssignmentSubmissionRequest
)
from app.exceptions import NotFoundError
from app.helpers.pagination import paginate_query
from datetime import datetime

def create_assignment(db: Session, assignment: AssignmentRequest, institution_id: Optional[int] = None) -> Assignment:
    """Create a new assignment"""
    assignment_dict = assignment.dict()
    # Set institution_id if provided, otherwise use from request
    if institution_id:
        assignment_dict['institution_id'] = institution_id
    elif 'institution_id' not in assignment_dict or assignment_dict['institution_id'] is None:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required to create an assignment")
    
    new_assignment = Assignment(**assignment_dict)
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    return new_assignment

def get_assignment(db: Session, assignment_id: int) -> Assignment:
    """Get an assignment by ID"""
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.deleted_at.is_(None)
    ).first()
    if not assignment:
        raise NotFoundError(f"Assignment with ID {assignment_id} not found")
    return assignment

def get_assignments(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    course_code: Optional[str] = None,
    institution_id: Optional[int] = None,
    lecturer_id: Optional[int] = None
) -> tuple[List[Assignment], int]:
    """Get list of assignments with pagination"""
    query = db.query(Assignment).filter(Assignment.deleted_at.is_(None))
    
    if institution_id:
        query = query.filter(Assignment.institution_id == institution_id)
    
    if lecturer_id:
        query = query.filter(Assignment.lecturer_id == lecturer_id)
    
    if course_code:
        query = query.filter(Assignment.course_code == course_code)
    
    return paginate_query(query, page=(skip // limit) + 1, page_size=limit)

def update_assignment(db: Session, assignment_id: int, assignment_update: AssignmentUpdate) -> Assignment:
    """Update an assignment"""
    assignment = get_assignment(db, assignment_id)
    
    update_data = assignment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assignment, field, value)
    
    db.commit()
    db.refresh(assignment)
    return assignment

def delete_assignment(db: Session, assignment_id: int) -> bool:
    """Soft delete an assignment"""
    assignment = get_assignment(db, assignment_id)
    assignment.deleted_at = datetime.utcnow()
    db.commit()
    return True

def submit_assignment(db: Session, submission: AssignmentSubmissionRequest) -> AssignmentSubmission:
    """Submit an assignment"""
    # Check if assignment exists
    assignment = get_assignment(db, submission.assignment_id)
    
    # Check if already submitted
    existing = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == submission.assignment_id,
        AssignmentSubmission.student_id == submission.student_id,
        AssignmentSubmission.deleted_at.is_(None)
    ).first()
    
    if existing:
        # Update existing submission
        existing.submission_file = submission.submission_file
        existing.submission_date = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new submission
    new_submission = AssignmentSubmission(
        assignment_id=submission.assignment_id,
        student_id=submission.student_id,
        submission_file=submission.submission_file,
        status="submitted"
    )
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)
    return new_submission

def get_student_submissions(db: Session, student_id: str) -> List[AssignmentSubmission]:
    """Get all submissions for a specific student"""
    return db.query(AssignmentSubmission).filter(
        AssignmentSubmission.student_id == student_id,
        AssignmentSubmission.deleted_at.is_(None)
    ).all()
