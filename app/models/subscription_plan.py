from sqlalchemy import Column, String, Integer, DateTime, Boolean, Numeric, Text
from app.database.base import DefaultBase
import datetime


class SubscriptionPlan(DefaultBase):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)  # "Freemium", "Premium"
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), default=0)
    billing_period = Column(String(20), nullable=True)  # monthly, quarterly, yearly
    is_active = Column(Boolean, default=True)
    features = Column(Text, nullable=True)  # JSON string of features
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
