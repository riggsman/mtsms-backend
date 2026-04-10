from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric
from app.database.base import DefaultBase
import datetime


class SubscriptionService(DefaultBase):
    """
    Subscription services model stored in the global database.
    Represents services that tenants can subscribe to.
    """

    __tablename__ = "subscription_services"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    billing_period = Column(String(50), nullable=False)  # monthly, yearly, one-time
    is_active = Column(Boolean, default=True, nullable=False)

    # Flags that indicate which subscription tiers this service belongs to.
    # These align with the Service Management UI checkboxes.
    is_freemium_enabled = Column(Boolean, default=False, nullable=False)
    is_premium_enabled = Column(Boolean, default=False, nullable=False)

    features = Column(Text, nullable=True)  # JSON string of features
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=True,
    )
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
