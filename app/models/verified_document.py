"""Issued academic documents (transcript / result slip) for public QR verification."""
import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, Index

from app.database.base_model import BaseModel_Base


class VerifiedDocument(BaseModel_Base):
    __tablename__ = "verified_documents"

    id = Column(Integer, primary_key=True)
    verification_token = Column(String(64), unique=True, nullable=False, index=True)
    document_type = Column(String(32), nullable=False)  # transcript | result_slip
    institution_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, nullable=True)
    student_no = Column(String(70), nullable=False)
    semester = Column(String(50), nullable=True)
    payload_json = Column(Text, nullable=False)
    issued_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_verified_documents_institution_student", "institution_id", "student_no"),
    )
