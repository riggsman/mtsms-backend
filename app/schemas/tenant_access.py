from typing import Optional
from pydantic import BaseModel


class TenantAccessStatusResponse(BaseModel):
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    domain: Optional[str] = None
    is_active: bool = True
    is_suspended: bool = False
    suspension_reason: Optional[str] = None
    suspended_at: Optional[str] = None
    services_activated: bool = False
    platform_support_email: Optional[str] = None
    platform_support_phone: Optional[str] = None
    platform_support_hours: Optional[str] = None
    activated_features_count: int = 0


class TenantActivationPatchRequest(BaseModel):
    services_activated: bool
