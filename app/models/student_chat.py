from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
import datetime

from app.database.base_model import BaseModel_Base


class StudentChatThread(BaseModel_Base):
    """
    staff: line between a student (student_owner_matricule) and staff; optional counterpart_user_id
    targets one staff member (otherwise any staff in the institution may pick up the thread).
    course: one thread per (institution, course_code); only enrolled students may access.
    direct: private chat between two students on the same course roster; student_owner_matricule
    and direct_peer_matricule store the two matricules in sorted order for stable de-duplication.
    """

    __tablename__ = "student_chat_threads"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    kind = Column(String(20), nullable=False)  # staff | course | direct
    course_code = Column(String(50), nullable=True, index=True)
    student_owner_matricule = Column(String(70), nullable=True, index=True)
    direct_peer_matricule = Column(String(70), nullable=True, index=True)
    counterpart_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    created_by_user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=True,
    )
    deleted_at = Column(DateTime, nullable=True)


class StudentChatMessage(BaseModel_Base):
    __tablename__ = "student_chat_messages"

    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("student_chat_threads.id"), nullable=False, index=True)
    parent_message_id = Column(Integer, ForeignKey("student_chat_messages.id"), nullable=True, index=True)
    sender_user_id = Column(Integer, nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    # Private threads (staff or student direct): recipient viewed thread → delivered_at/read_at on sender's messages
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
