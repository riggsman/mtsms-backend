from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text
import datetime
from app.database.base import DefaultBase


class ContactMessage(DefaultBase):
    """
    Stores messages sent via the public contact form.
    Lives in the global/shared database so system/admin users can manage all messages
    without requiring tenant headers.
    """

    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    phone = Column(String(100), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    reply_subject = Column(String(200), nullable=True)
    reply_message = Column(Text, nullable=True)
    replied_at = Column(DateTime, nullable=True)
    replied_by = Column(String(200), nullable=True)
    replied_by_role = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=True,
    )
    deleted_at = Column(DateTime, nullable=True)

