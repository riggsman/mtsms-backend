import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database.sessionManager import BaseModel_Base


class UserPushToken(BaseModel_Base):
    """
    FCM registration tokens for web push, scoped to tenant DB (one row per user+device token).
    """

    __tablename__ = "user_push_tokens"
    __table_args__ = (UniqueConstraint("user_id", "token", name="uq_user_push_tokens_user_token"),)

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(Text, nullable=False)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
