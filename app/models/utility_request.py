from sqlalchemy import Column, String, Integer, DateTime, Text, Enum
from app.database.base_model import BaseModel_Base
import datetime
import enum

class UtilityRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class UtilityRequest(BaseModel_Base):
    __tablename__ = "utility_requests"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False)
    requested_by = Column(Integer, nullable=True)  # user_id, nullable for anonymous
    utility_type = Column(String(50), nullable=False)  # electricity, water, internet, gas, maintenance, other
    location = Column(String(200), nullable=True)  # building, room, area description
    description = Column(Text, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected, in_progress, completed
    handled_by = Column(Integer, nullable=True)  # user_id of staff handling it
    handled_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
