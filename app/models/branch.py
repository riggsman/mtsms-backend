"""Campus / branch per institution (e.g. Douala, Yaoundé)."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric
from app.database.base_model import BaseModel_Base
import datetime


class Branch(BaseModel_Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    name = Column(String(200), nullable=False)  # e.g. town / campus label
    code = Column(String(64), nullable=True)  # optional short code
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Fee structure fields per branch/school
    fee_amount = Column(Numeric(10, 2), nullable=True, default=0)  # Total fee amount for this school
    fee_deadline = Column(DateTime, nullable=True)  # Final payment deadline for this school
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=True,
    )
