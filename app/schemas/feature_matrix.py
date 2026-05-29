from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class FeatureMatrixItemResponse(BaseModel):
    button_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    service_id: Optional[int] = None
    enabled: bool = False
    freemium: bool = False
    premium: bool = False
    monetized: bool = False
    amount: Optional[float] = None
    menuIds: List[str] = Field(default_factory=list)
    nameAliases: List[str] = Field(default_factory=list)


class FeatureMatrixResponse(BaseModel):
    items: List[FeatureMatrixItemResponse]


class FeatureMatrixUpdateItem(BaseModel):
    button_id: str = Field(..., min_length=1)
    enabled: bool = False
    freemium: bool = False
    premium: bool = False
    monetized: bool = False
    amount: Optional[float] = Field(None, ge=0)


class FeatureMatrixUpdateRequest(BaseModel):
    items: List[FeatureMatrixUpdateItem]


class TenantFeaturesResponse(BaseModel):
    plan: str
    features: Dict[str, bool]


class TenantFeatureMatrixItemResponse(BaseModel):
    button_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    global_enabled: bool = False
    plan_allowed: bool = False
    enabled_for_tenant: bool = False
    effective: bool = False
    menuIds: List[str] = Field(default_factory=list)


class TenantFeatureMatrixResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    plan: str
    items: List[TenantFeatureMatrixItemResponse]


class TenantFeatureMatrixUpdateItem(BaseModel):
    button_id: str = Field(..., min_length=1)
    enabled_for_tenant: bool = False


class TenantFeatureMatrixUpdateRequest(BaseModel):
    items: List[TenantFeatureMatrixUpdateItem]
