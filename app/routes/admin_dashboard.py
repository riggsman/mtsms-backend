"""Tenant admin dashboard overview API."""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import require_tenant_permission
from app.dependencies.institutionDependency import get_institution_id_from_header
from app.dependencies.tenantDependency import get_db
from app.helpers.tenant_scope import institution_id_for_user
from app.models.user import User
from app.services.admin_dashboard_queries import get_admin_dashboard_overview

router = APIRouter()


@router.get("/admin/dashboard/overview")
def admin_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_permission("view_analytics")),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
):
    """Aggregated stats, trends, and recent reports for the tenant admin overview page."""
    institution_id = institution_id_for_user(
        current_user,
        header_institution_id=header_institution_id,
    )
    return get_admin_dashboard_overview(db, institution_id)
