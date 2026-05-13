from sqlalchemy import Column, String, Integer, DateTime, Text, Enum, ForeignKey
from app.database.sessionManager import BaseModel_Base
import datetime
import enum

class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class LeaveRequest(BaseModel_Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    leave_type = Column(String(50), nullable=False)  # sick, annual, maternity, paternity, unpaid, other
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)