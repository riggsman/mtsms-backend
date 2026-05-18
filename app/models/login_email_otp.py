from sqlalchemy import Column, DateTime, Integer, String

from app.database.sessionManager import BaseModel_Base
import datetime


class LoginEmailOtp(BaseModel_Base):
    """One-time email codes for passwordless tenant login (10-minute TTL, single use)."""

    __tablename__ = "login_email_otps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    code_hash = Column(String(200), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
