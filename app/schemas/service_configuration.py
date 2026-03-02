from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ServiceConfigurationRequest(BaseModel):
    """Request model for creating/updating service configurations"""

    service_name: str = Field(..., min_length=1, max_length=200, description="Service name")
    configuration_key: str = Field(..., min_length=1, max_length=200, description="Configuration key")
    configuration_value: Optional[str] = Field(None, description="Configuration value (can be JSON string)")
    description: Optional[str] = Field(None, description="Configuration description")
    is_active: bool = Field(default=True, description="Whether the configuration is active")
    tenant_id: Optional[int] = Field(None, description="Tenant ID (null for global config)")


class ServiceConfigurationResponse(BaseModel):
    """Response model for service configurations"""

    id: int
    service_name: str
    configuration_key: str
    configuration_value: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    tenant_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ServiceConfigurationBulkRequest(BaseModel):
    """Request model for bulk creating/updating service configurations"""

    service_name: str = Field(..., min_length=1, max_length=200, description="Service name")
    configurations: Dict[str, Any] = Field(..., description="Dictionary of configuration key-value pairs")
    description: Optional[str] = Field(None, description="Overall description for these configurations")
    tenant_id: Optional[int] = Field(None, description="Tenant ID (null for global config)")


class ServiceConfigurationUpdateItem(BaseModel):
    """Individual configuration item for bulk update"""

    service_id: int = Field(..., description="Subscription service ID")
    subscription_type: str = Field(..., description="Subscription type (e.g., freemium, premium)")
    is_enabled: bool = Field(..., description="Whether this subscription type is enabled")


class ServiceConfigurationUpdateRequest(BaseModel):
    """Request model for updating service configurations via PUT"""

    configurations: list[ServiceConfigurationUpdateItem] = Field(..., description="List of configuration items to update")
