from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from app.database.base import DefaultBase
import datetime


class ServiceConfiguration(DefaultBase):
    """
    Service configuration model stored in the global database.
    Represents configuration settings for various services in the system.
    """

    __tablename__ = "service_configurations"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(200), nullable=False, index=True)
    configuration_key = Column(String(200), nullable=False, index=True)
    configuration_value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)  # NULL = global config
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=True,
    )
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
