from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from app.database.sessionManager import BaseModel_Base
import datetime

class StaffAttendance(BaseModel_Base):
    __tablename__ = "staff_attendance"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    clock_in = Column(DateTime, nullable=True)
    clock_out = Column(DateTime, nullable=True)
    status = Column(String(20), default="present")  # present, absent, late, half_day
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
