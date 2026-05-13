from sqlalchemy import Column, String, Integer, DateTime, Boolean, Numeric, Text
from app.database.base import DefaultBase
import datetime

class Tenant(DefaultBase):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True)
    name = Column(String(70), nullable=False, unique=True)
    category = Column(String(10), nullable=False)  # HI or SI
    database_url = Column(String(200), nullable=True)
    domain = Column(String(200), nullable=True)
    logo_url = Column(String(500), nullable=True)  # URL to tenant logo file
    is_active = Column(Boolean, default=True, nullable=False)
    suspension_reason = Column(Text, nullable=True)
    suspended_at = Column(DateTime, nullable=True)
    fee_amount = Column(Numeric(10, 2), nullable=True, default=0)  # Total fee amount
    fee_deadline = Column(DateTime, nullable=True)  # Final payment deadline
    subscription_plan = Column(String(64), nullable=True)  # e.g. Freemium, Premium
    subscription_started_at = Column(DateTime, nullable=True)  # Current billing period start
    billing_type = Column(String(20), nullable=True)  # monthly, quarterly, yearly
    payment_date = Column(DateTime, nullable=True)  # Payment date for premium users
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)