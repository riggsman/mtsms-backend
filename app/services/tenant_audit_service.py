"""Record tenant lifecycle audit events."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.tenant_audit import TenantAuditEvent


def record_tenant_audit_event(
    db: Session,
    *,
    tenant_id: int,
    action: str,
    reason: Optional[str] = None,
    actor_user_id: Optional[int] = None,
) -> TenantAuditEvent:
    event = TenantAuditEvent(
        tenant_id=tenant_id,
        action=action,
        reason=(reason or "")[:4000] or None,
        actor_user_id=actor_user_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
