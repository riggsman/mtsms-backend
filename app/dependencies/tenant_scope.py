"""FastAPI dependencies for tenant-scoped institution_id."""

from typing import Optional

from fastapi import Depends

from app.dependencies.auth import get_current_user_tenant
from app.dependencies.institutionDependency import get_institution_id_from_header
from app.helpers.tenant_scope import institution_id_for_user
from app.models.user import User


def get_scoped_institution_id(
    current_user: User = Depends(get_current_user_tenant),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
) -> Optional[int]:
    """Resolved institution_id for list/detail routes (None = system admin, all tenants)."""
    return institution_id_for_user(current_user, header_institution_id=header_institution_id)
