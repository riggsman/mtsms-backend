import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Integer, Numeric, String, UniqueConstraint

from app.database.sessionManager import BaseModel_Base


class StudentCourseRank(BaseModel_Base):
    __tablename__ = "student_course_ranks"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    student_id = Column(String(70), nullable=False, index=True)
    course_code = Column(String(50), nullable=False, index=True)
    academic_year = Column(String(32), nullable=False, index=True)
    semester_or_term = Column(String(32), nullable=False, index=True)
    score = Column(Numeric(8, 2), nullable=False, default=0)
    dense_rank = Column(Integer, nullable=False, index=True)
    computed_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)
    source_updated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "student_id",
            "course_code",
            "academic_year",
            "semester_or_term",
            name="uq_student_course_rank_scope",
        ),
        CheckConstraint("dense_rank >= 1", name="ck_student_course_rank_dense_rank_positive"),
    )
