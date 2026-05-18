"""
Provision tenant User accounts for guardians (parent role) using the email
collected at student admission, so parents can sign in with that email.
"""
from __future__ import annotations

import logging
import re
import secrets
import uuid
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.authentication.authenticator import hash_password
from app.helpers.user_roles import roles_to_storage_value, user_roles_list
from app.models.user import User

logger = logging.getLogger(__name__)


def _split_guardian_name(name: Optional[str]) -> Tuple[str, str]:
    raw = (name or "").strip()
    if not raw:
        return "Parent", "User"
    parts = re.split(r"\s+", raw)
    if len(parts) == 1:
        return parts[0], "User"
    return parts[0], parts[-1]


def _unique_username(db: Session, institution_id: int, email: str) -> str:
    """User.username is max 50 chars and globally unique."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "", (email.split("@")[0] if "@" in email else email))[:12] or "parent"
    for _ in range(20):
        candidate = f"p{institution_id}_{slug}_{uuid.uuid4().hex[:6]}"[:50]
        if not db.query(User.id).filter(User.username == candidate).first():
            return candidate
    return f"p{institution_id}_{uuid.uuid4().hex[:16]}"[:50]


def sync_parent_user_for_guardian(
    db: Session,
    *,
    institution_id: int,
    guardian_email: Optional[str],
    guardian_name: Optional[str],
    guardian_phone: Optional[str] = None,
    guardian_address: Optional[str] = None,
) -> Optional[str]:
    """
    Create or update a tenant user with role `parent` matching guardian_email.
    New accounts receive a random password and must_change_password=true.

    Returns the plain temporary password when a **new** user was created (for optional email),
    otherwise None.
    """
    email = (guardian_email or "").strip()
    if not email or "@" not in email:
        return None

    email = email[:70]
    phone = (guardian_phone or "").strip() or "0000000000"
    address = (guardian_address or "").strip() or "N/A"
    first, last = _split_guardian_name(guardian_name)

    existing = (
        db.query(User)
        .filter(func.lower(User.email) == email.lower(), User.deleted_at.is_(None))
        .first()
    )

    if existing:
        if existing.institution_id != institution_id:
            logger.info(
                "Skipping parent role sync: email %s already used by user in another institution",
                email,
            )
            return None
        roles = list(user_roles_list(existing))
        if "parent" not in roles:
            roles.append("parent")
            existing.role = roles_to_storage_value(roles)
        return None

    plain_password = secrets.token_urlsafe(14)
    new_user = User(
        institution_id=institution_id,
        branch_id=None,
        department_id=None,
        position="parent",
        firstname=first[:70],
        middlename=None,
        lastname=last[:70],
        gender="Unknown",
        address=address[:200],
        email=email,
        phone=phone[:200],
        username=_unique_username(db, institution_id, email),
        password=hash_password(plain_password),
        role=roles_to_storage_value(["parent"]),
        user_type="TENANT",
        is_active="active",
        must_change_password="true",
        language="en",
    )
    db.add(new_user)
    logger.info("Created parent portal user for email %s (institution_id=%s)", email, institution_id)
    return plain_password
