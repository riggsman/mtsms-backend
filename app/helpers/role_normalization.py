"""Canonical role strings stored in DB and returned in APIs."""
from typing import Optional


def normalize_user_role_string(raw_role: Optional[str]) -> str:
    """
    Normalize comma-separated roles: lecturer/teacher/staff -> staff (canonical teaching role).
    """
    if not raw_role:
        return ""
    items = [r.strip().lower() for r in str(raw_role).split(",") if r.strip()]
    normalized = []
    for role in items:
        if role in {"lecturer", "teacher", "staff"}:
            role = "staff"
        if role not in normalized:
            normalized.append(role)
    return ",".join(normalized)
