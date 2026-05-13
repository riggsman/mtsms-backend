from sqlalchemy import Column, DateTime, String, Integer, ForeignKey, JSON
from app.database.sessionManager import BaseModel_Base
import datetime

class User(BaseModel_Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=True)  # Can be None for system users
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)  # Campus; super_admin often null = all branches
    department_id = Column(Integer, nullable=True)
    position = Column(String(120), nullable=True)
    firstname = Column(String(70), nullable=False)
    middlename = Column(String(200), nullable=True)
    lastname = Column(String(70), nullable=False)
    gender = Column(String(70), nullable=False)
    address = Column(String(200), nullable=False)
    email = Column(String(70), nullable=False, unique=True)
    phone = Column(String(200), nullable=False)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(200), nullable=False)
    # JSON array of role strings, e.g. ["admin","staff"]
    role = Column(JSON, nullable=False)
    # Extra capabilities for SYSTEM users (e.g. ["database_config"]), granted by system_super_admin
    system_permissions = Column(JSON, nullable=True)
    user_type = Column(String(20), default="TENANT", nullable=False)  # TENANT or SYSTEM - indicates if user was created by tenant admin or system admin
    is_active = Column(String(10), default="active", nullable=False)  # active, inactive, suspended
    must_change_password = Column(String(10), default="false", nullable=False)  # true, false - indicates if user must change password on first login
    profile_picture = Column(String(500), nullable=True)  # Path to profile picture file
    language = Column(String(8), nullable=False, default="en")  # User preferred language (en, fr, etc.)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
   