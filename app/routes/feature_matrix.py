from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database.base import get_db_session
from app.dependencies.auth import get_current_user
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
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    _require_system_admin(current_user)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    updates = [item.model_dump() for item in payload.items]
    data = fas.save_tenant_feature_matrix(db, tenant, updates)
    return TenantFeatureMatrixResponse(
        tenant_id=data["tenant_id"],
        tenant_name=data["tenant_name"],
        plan=data["plan"],
        items=[TenantFeatureMatrixItemResponse(**row) for row in data["items"]],
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
):
    tenant = fas.resolve_tenant(
        db,
        institution_id=getattr(current_user, "institution_id", None),
        domain=x_tenant_domain,
    )
    plan = fas.normalize_plan(tenant.subscription_plan if tenant else None)
    features = fas.get_tenant_features(db, tenant)
    return TenantFeaturesResponse(plan=plan, features=features)
