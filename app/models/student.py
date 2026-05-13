from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from app.database.sessionManager import BaseModel_Base
import datetime

class Student(BaseModel_Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False)  # Multi-tenancy isolation
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    school_id = Column(Integer, nullable=False)  # References schools table but FK removed (from departments table)
    firstname = Column(String(70), nullable=False)
    middlename = Column(String(200), nullable=True)
    lastname = Column(String(70), nullable=False)
    dob = Column(String(200), nullable=False)
    gender = Column(String(70), nullable=False)
    address = Column(String(200), nullable=False)
    email = Column(String(70), nullable=False, unique=True)
    phone = Column(String(200), nullable=False)
    student_id = Column(String(70), nullable=False, unique=True)  # Student registration number
    class_id = Column(Integer, nullable=False)
    level = Column(String(20), nullable=False)
    type = Column(String(20), nullable=False, default="Undergraduate")  # regular, transfer, etc.
    # Integer FKs only — Department/Specialization live on DefaultBase metadata, Student on BaseModel_Base,
    # so ForeignKey("…") strings cannot resolve across metadatas (NoReferencedTableError at mapper configure).
    department_id = Column(Integer, nullable=False)
    specialization_id = Column(Integer, nullable=True)
    academic_year_id = Column(Integer, nullable=False)
    guardian_id = Column(Integer, nullable=False)
    place_of_birth = Column(String(200), nullable=True)  # Student's place of birth
    degree_proposed = Column(String(100), nullable=True)  # Degree program being enrolled
    photo = Column(String(500), nullable=True)  # Store photo file path (relative from uploads)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete