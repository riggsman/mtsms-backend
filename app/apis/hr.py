from sqlalchemy.orm import Session
from app.models.staff_document import StaffDocument
from app.models.staff_attendance import StaffAttendance
from app.schemas.hr import StaffDocumentCreate, StaffAttendanceCreate
from typing import Optional, List
from datetime import datetime

# Staff Documents
def create_staff_document(db: Session, doc_data: StaffDocumentCreate, institution_id: int):
    db_doc = StaffDocument(
        institution_id=institution_id,
        staff_id=doc_data.staff_id,
        document_type=doc_data.document_type,
        file_name=doc_data.file_name,
        file_path=doc_data.file_path,
        expiry_date=doc_data.expiry_date,
        notes=doc_data.notes
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

def get_staff_documents(db: Session, institution_id: int, staff_id: Optional[int] = None):
    query = db.query(StaffDocument).filter(StaffDocument.institution_id == institution_id, StaffDocument.deleted_at == None)
    if staff_id:
        query = query.filter(StaffDocument.staff_id == staff_id)
    return query.all()

# Staff Attendance
def mark_staff_attendance(db: Session, attendance_data: StaffAttendanceCreate, institution_id: int):
    # Check if attendance already exists for this staff on this day
    date_only = attendance_data.date.date()
    existing = db.query(StaffAttendance).filter(
        StaffAttendance.institution_id == institution_id,
        StaffAttendance.staff_id == attendance_data.staff_id,
        StaffAttendance.date >= datetime.combine(date_only, datetime.min.time()),
        StaffAttendance.date <= datetime.combine(date_only, datetime.max.time()),
        StaffAttendance.deleted_at == None
    ).first()

    if existing:
        if attendance_data.clock_in:
            existing.clock_in = attendance_data.clock_in
        if attendance_data.clock_out:
            existing.clock_out = attendance_data.clock_out
        if attendance_data.status:
            existing.status = attendance_data.status
        if attendance_data.notes:
            existing.notes = attendance_data.notes
        db.commit()
        db.refresh(existing)
        return existing
    
    db_attendance = StaffAttendance(
        institution_id=institution_id,
        staff_id=attendance_data.staff_id,
        date=attendance_data.date,
        clock_in=attendance_data.clock_in,
        clock_out=attendance_data.clock_out,
        status=attendance_data.status,
        notes=attendance_data.notes
    )
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance

def get_staff_attendance(db: Session, institution_id: int, staff_id: Optional[int] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    query = db.query(StaffAttendance).filter(StaffAttendance.institution_id == institution_id, StaffAttendance.deleted_at == None)
    if staff_id:
        query = query.filter(StaffAttendance.staff_id == staff_id)
    if start_date:
        query = query.filter(StaffAttendance.date >= start_date)
    if end_date:
        query = query.filter(StaffAttendance.date <= end_date)
    return query.all()
