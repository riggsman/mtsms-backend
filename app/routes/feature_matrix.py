from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database.base import get_db_session
from app.dependencies.auth import get_current_user
from app.dependencies.tenant_activation import (
    count_activated_features,
    get_platform_support_settings,
    is_tenant_services_activated,
    is_tenant_suspended,
    resolve_tenant_for_user,
    set_tenant_services_activated,
)
from app.helpers.user_roles import user_is_system_admin
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.feature_matrix import (
    FeatureMatrixResponse,
    FeatureMatrixItemResponse,
    FeatureMatrixUpdateRequest,
    TenantFeaturesResponse,
    TenantFeatureMatrixResponse,
    TenantFeatureMatrixItemResponse,
    TenantFeatureMatrixUpdateRequest,
)
from app.schemas.tenant_access import TenantAccessStatusResponse, TenantActivationPatchRequest
from app.services import feature_access_service as fas

feature_matrix = APIRouter()


def _require_system_admin(current_user: User) -> None:
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin or system super admin can manage feature matrix",
        )


@feature_matrix.get(
    "/admin/feature-matrix",
    response_model=FeatureMatrixResponse,
    tags=["Feature Matrix"],
)
def get_admin_feature_matrix(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    _require_system_admin(current_user)
    rows = fas.get_feature_matrix(db)
    return FeatureMatrixResponse(
        items=[FeatureMatrixItemResponse(**row) for row in rows]
    )


@feature_matrix.put(
    "/admin/feature-matrix",
    response_model=FeatureMatrixResponse,
    tags=["Feature Matrix"],
)
def put_admin_feature_matrix(
    payload: FeatureMatrixUpdateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    _require_system_admin(current_user)
    updates = [item.model_dump() for item in payload.items]
    rows = fas.save_feature_matrix(db, updates)
    return FeatureMatrixResponse(
        items=[FeatureMatrixItemResponse(**row) for row in rows]
    )


@feature_matrix.post(
    "/admin/feature-matrix/sync-catalog",
    tags=["Feature Matrix"],
)
def sync_feature_catalog(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    _require_system_admin(current_user)
    created = fas.sync_catalog_to_db(db)
    rows = fas.get_feature_matrix(db)
    return {
        "created": created,
        "items": [FeatureMatrixItemResponse(**row) for row in rows],
    }


@feature_matrix.get(
    "/admin/tenants/{tenant_id}/features",
    response_model=TenantFeatureMatrixResponse,
    tags=["Feature Matrix"],
)
def get_admin_tenant_feature_matrix(
    tenant_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    _require_system_admin(current_user)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    data = fas.get_tenant_feature_matrix(db, tenant)
    return TenantFeatureMatrixResponse(
        tenant_id=data["tenant_id"],
        tenant_name=data["tenant_name"],
        plan=data["plan"],
        items=[TenantFeatureMatrixItemResponse(**row) for row in data["items"]],
    )


@feature_matrix.put(
    "/admin/tenants/{tenant_id}/features",
    response_model=TenantFeatureMatrixResponse,
    tags=["Feature Matrix"],
)
def put_admin_tenant_feature_matrix(
    tenant_id: int,
    payload: TenantFeatureMatrixUpdateRequest,
    activate: bool = Query(False, description="Activate tenant services after save if at least one feature is enabled"),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    _require_system_admin(current_user)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    updates = [item.model_dump() for item in payload.items]
    data = fas.save_tenant_feature_matrix(db, tenant, updates)
    db.refresh(tenant)
    if activate:
        set_tenant_services_activated(
            db,
            tenant,
            activated=True,
            activated_by_user_id=current_user.id,
            require_features_when_activating=True,
        )
    return TenantFeatureMatrixResponse(
        tenant_id=data["tenant_id"],
        tenant_name=data["tenant_name"],
        plan=data["plan"],
        items=[TenantFeatureMatrixItemResponse(**row) for row in data["items"]],
    )


@feature_matrix.patch(
    "/admin/tenants/{tenant_id}/activation",
    tags=["Feature Matrix"],
)
def patch_tenant_activation(
    tenant_id: int,
    payload: TenantActivationPatchRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    _require_system_admin(current_user)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant = set_tenant_services_activated(
        db,
        tenant,
        activated=payload.services_activated,
        activated_by_user_id=current_user.id if payload.services_activated else None,
        require_features_when_activating=payload.services_activated,
    )
    return {
        "tenant_id": tenant.id,
        "services_activated": tenant.services_activated,
        "services_activated_at": tenant.services_activated_at,
        "activated_features_count": count_activated_features(db, tenant),
    }


@feature_matrix.get(
    "/tenant/access-status",
    response_model=TenantAccessStatusResponse,
    tags=["Feature Matrix"],
)
def get_tenant_access_status(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    x_tenant_domain: Optional[str] = Header(None, alias="X-Tenant-Domain"),
    x_tenant_name: Optional[str] = Header(None, alias="X-Tenant-Name"),
):
    tenant = resolve_tenant_for_user(db, current_user, x_tenant_domain, x_tenant_name)
    try:
        support = get_platform_support_settings(db)
    except Exception:
        support = {
            "platform_support_email": None,
            "platform_support_phone": None,
            "platform_support_hours": None,
        }
    try:
        activated_count = count_activated_features(db, tenant)
    except Exception:
        activated_count = 0
    suspended = is_tenant_suspended(tenant, db)
    suspended_at = None
    if tenant and tenant.suspended_at is not None:
        suspended_at = tenant.suspended_at.isoformat()

    return TenantAccessStatusResponse(
        tenant_id=tenant.id if tenant else None,
        tenant_name=tenant.name if tenant else None,
        domain=tenant.domain if tenant else None,
        is_active=bool(tenant.is_active) if tenant else True,
        is_suspended=suspended,
        suspension_reason=tenant.suspension_reason if tenant else None,
        suspended_at=suspended_at,
        services_activated=is_tenant_services_activated(tenant, db),
        platform_support_email=support.get("platform_support_email"),
        platform_support_phone=support.get("platform_support_phone"),
        platform_support_hours=support.get("platform_support_hours"),
        activated_features_count=activated_count,
    )


@feature_matrix.get(
    "/tenant/features",
    response_model=TenantFeaturesResponse,
    tags=["Feature Matrix"],
)
def get_tenant_feature_flags(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    x_tenant_domain: Optional[str] = Header(None, alias="X-Tenant-Domain"),
    x_tenant_name: Optional[str] = Header(None, alias="X-Tenant-Name"),
):
    tenant = resolve_tenant_for_user(db, current_user, x_tenant_domain, x_tenant_name)
    plan = fas.normalize_plan(tenant.subscription_plan if tenant else None)
    features = fas.get_tenant_features(db, tenant)
    return TenantFeaturesResponse(plan=plan, features=features)
