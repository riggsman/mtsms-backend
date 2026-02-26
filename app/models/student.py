from sqlalchemy import Column, String, Integer, DateTime
from app.database.sessionManager import BaseModel_Base
import datetime

class Student(BaseModel_Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
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
    department_id = Column(Integer, nullable=False)
    academic_year_id = Column(Integer, nullable=False)
    guardian_id = Column(Integer, nullable=False)
    photo = Column(String(5000), nullable=True)  # Store base64 encoded photo or photo URL
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete