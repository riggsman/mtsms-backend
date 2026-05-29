import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.database.base import DefaultBase

# If you use relationships, also import:
# from sqlalchemy.orm import relationship


class Specialization(DefaultBase):
    __tablename__ = "specializations"   # or "specialties" if you prefer American spelling
    id = Column(Integer, primary_key=True)
    # Multi-tenancy isolation (same as Department)
    institution_id = Column(Integer, ForeignKey("tenants.id"),nullable=False, index=True)
    # Link to the parent Department
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False, unique=True)   # e.g., "CS-AI", "MED-SURG"
    description = Column(Text, nullable=True)
    # Optional: Head of the specialization (could be a Teacher/Lecturer ID)
    head_id = Column(Integer, nullable=True)   # Teacher ID who heads this specialization
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.datetime.utcnow, 
        onupdate=datetime.datetime.utcnow, 
        nullable=True
    )
    deleted_at = Column(DateTime, nullable=True)   # Soft delete
