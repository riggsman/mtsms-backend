from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict
from datetime import date, timedelta
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
    lecturer_id: Optional[int] = None,
    lifecycle: Optional[str] = None,
    due_window_days: int = 14,
) -> tuple[List[Assignment], int]:
    """Get list of assignments with pagination.

    lifecycle:
      - "active": still open for submission (due date today or later, or past due with late_penalty > 0)
      - "due": past due, or due date within the next ``due_window_days`` calendar days (inclusive)
    """
    query = db.query(Assignment).filter(Assignment.deleted_at.is_(None))

    if institution_id:
        query = query.filter(Assignment.institution_id == institution_id)

    if lecturer_id:
        query = query.filter(Assignment.lecturer_id == lecturer_id)

    if course_code:
        query = query.filter(Assignment.course_code == course_code)

    if lifecycle in ("active", "due"):
        due_eff = func.coalesce(Assignment.extended_due_date, Assignment.due_date)
        today = date.today()
        lp = func.coalesce(Assignment.late_penalty, 0)
        if lifecycle == "active":
            query = query.filter(
                or_(
                    due_eff >= today,
                    and_(due_eff < today, lp > 0),
                )
            )
        else:
            horizon_days = max(1, min(int(due_window_days), 366))
            horizon = today + timedelta(days=horizon_days)
            query = query.filter(
                or_(
                    due_eff < today,
                    and_(due_eff >= today, due_eff <= horizon),
                )
            )

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
    from app.helpers.file_upload import delete_file
    
    # Check if assignment exists
    assignment = get_assignment(db, submission.assignment_id)
    
    # Check if already submitted
    existing = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == submission.assignment_id,
        AssignmentSubmission.student_id == submission.student_id,
        AssignmentSubmission.deleted_at.is_(None)
    ).first()
    
    if existing:
        # Delete old file if it exists and is different from new file
        old_file = existing.submission_file
        if old_file and old_file != submission.submission_file:
            # Extract relative path from URL (files are stored as URLs)
            if old_file.startswith('/api/v1/uploads/'):
                relative_path = old_file.replace('/api/v1/uploads/', '')
                try:
                    delete_file(relative_path)
                except Exception as e:
                    print(f"Warning: Could not delete old submission file: {e}")
        
        # Update existing submission
        existing.submission_file = submission.submission_file
        existing.submission_date = datetime.utcnow()
        # Store note in feedback field if note field doesn't exist in model
        # (Note: If model has note field, use that instead)
        if hasattr(existing, 'note'):
            existing.note = submission.note
        elif submission.note:
            # Store note in feedback if note field doesn't exist
            existing.feedback = submission.note if not existing.feedback else f"{existing.feedback}\n\nNote: {submission.note}"
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new submission
    submission_data = {
        "assignment_id": submission.assignment_id,
        "student_id": submission.student_id,
        "submission_file": submission.submission_file,
        "status": "submitted",
        "institution_id": assignment.institution_id
    }
    
    # Add note if model supports it, otherwise store in feedback
    if hasattr(AssignmentSubmission, 'note'):
        submission_data["note"] = submission.note
    elif submission.note:
        submission_data["feedback"] = submission.note
    
    new_submission = AssignmentSubmission(**submission_data)
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


def get_submission_counts_by_institution(db: Session, institution_id: int) -> Dict[int, int]:
    """Count non-deleted submissions per assignment for an institution."""
    rows = (
        db.query(AssignmentSubmission.assignment_id, func.count(AssignmentSubmission.id))
        .filter(
            AssignmentSubmission.institution_id == institution_id,
            AssignmentSubmission.deleted_at.is_(None),
        )
        .group_by(AssignmentSubmission.assignment_id)
        .all()
    )
    return {int(aid): int(n) for aid, n in rows}


def list_submissions_for_assignment(
    db: Session,
    assignment_id: int,
    institution_id: int,
) -> List[AssignmentSubmission]:
    """All submissions for one assignment (tenant-scoped)."""
    assignment = get_assignment(db, assignment_id)
    if assignment.institution_id != institution_id:
        raise NotFoundError(f"Assignment with ID {assignment_id} not found")
    return (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.institution_id == institution_id,
            AssignmentSubmission.deleted_at.is_(None),
        )
        .order_by(AssignmentSubmission.submission_date.desc())
        .all()
    )
