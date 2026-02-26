from sqlalchemy import Column, String, Integer, DateTime
from app.database.sessionManager import BaseModel_Base
import datetime

class Guardian(BaseModel_Base):
    __tablename__ = "guardians"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    guardian_name = Column(String(200), nullable=False)
    phone = Column(String(200), nullable=False)
    address = Column(String(200), nullable=False)
    relationship = Column(String(70), nullable=False)  # father, mother, guardian, etc.
    gender = Column(String(70), nullable=False)
    email = Column(String(70), nullable=True)
    occupation = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
