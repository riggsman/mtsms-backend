"""Per-tenant feature overrides (global DB)."""
import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String

from app.database.base import DefaultBase


class TenantFeatureEntitlement(DefaultBase):
    __tablename__ = "tenant_feature_entitlements"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    button_id = Column(String(120), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_tenant_feature_entitlement_unique", "tenant_id", "button_id", unique=True),
    )
