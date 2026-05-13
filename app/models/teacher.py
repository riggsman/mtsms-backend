from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric
from app.database.sessionManager import BaseModel_Base
import datetime

class Teacher(BaseModel_Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False)  # Multi-tenancy isolation
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    firstname = Column(String(70), nullable=False)
    middlename = Column(String(200), nullable=True)
    lastname = Column(String(70), nullable=False)
    dob = Column(String(200), nullable=False)
    gender = Column(String(70), nullable=False)
    address = Column(String(200), nullable=False)
    email = Column(String(70), nullable=False, unique=True)
    phone = Column(String(200), nullable=False)
    department_id = Column(Integer, nullable=False)
    employee_id = Column(String(70), nullable=False, unique=True)
    position = Column(String(120), nullable=True)
    qualification = Column(String(200), nullable=True)
    specialization = Column(String(200), nullable=True)
    hourly_rate = Column(Numeric(12, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
