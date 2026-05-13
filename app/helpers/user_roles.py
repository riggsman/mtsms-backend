"""
Multi-role support: roles are stored as a JSON array of strings on User.role
(e.g. ["admin","staff"]). Legacy comma-separated strings and single values are still parsed.
"""
from __future__ import annotations

import json
from typing import Any, List, Optional, Union

import sqlalchemy as sa
from sqlalchemy import func

from app.helpers.role_normalization import normalize_user_role_string

# Priority for picking a single "primary" role for routing / legacy `role` string (highest first)
_ROLE_PRIORITY = (
    "system_super_admin",
    "system_admin",
    "super_admin",
    "admin",
    "secretary",
    "staff",
    "teacher",
    "lecturer",
    "student",
    "parent",
)


def parse_roles_to_list(raw: Any) -> List[str]:
    """Normalize any legacy or new storage shape into a list of role strings."""
    if raw is None:
        return []
    if isinstance(raw, list):
        items = [str(x).strip().lower() for x in raw if x is not None and str(x).strip()]
    elif isinstance(raw, dict):
        # unexpected; treat values as roles
        items = [str(v).strip().lower() for v in raw.values() if v]
    else:
        s = str(raw).strip()
        if not s:
            return []
        if s.startswith("["):
            try:
                data = json.loads(s)
                if isinstance(data, list):
                    items = [str(x).strip().lower() for x in data if x is not None and str(x).strip()]
                else:
                    items = [s.lower()]
            except (json.JSONDecodeError, TypeError):
                items = [p.strip().lower() for p in s.split(",") if p.strip()]
        else:
            items = [p.strip().lower() for p in s.split(",") if p.strip()]

    # Canonical: staff/lecturer/teacher collapse to staff
    out: List[str] = []
    for r in items:
        if r in {"lecturer", "teacher", "staff"}:
            r = "staff"
        if r and r not in out:
            out.append(r)
    return out


def normalize_roles_for_storage(raw: Union[str, List[str], None]) -> List[str]:
    """Build canonical list for persisting to JSON column."""
    if raw is None:
        return []
    if isinstance(raw, list):
        merged = ",".join(str(x).strip() for x in raw if str(x).strip())
    else:
        merged = str(raw).strip()
    if not merged:
        return []
    # Reuse comma normalizer then split back to list
    normalized = normalize_user_role_string(merged)
    if not normalized:
        return []
    return [p.strip() for p in normalized.split(",") if p.strip()]


def roles_to_storage_value(roles: List[str]) -> List[str]:
    """Return a copy suitable for assigning to User.role JSON column."""
    return normalize_roles_for_storage(roles)


def user_roles_list(user: Any) -> List[str]:
    """Roles for a User ORM object (or any object with .role)."""
    if user is None:
        return []
    return parse_roles_to_list(getattr(user, "role", None))


def user_has_role(user: Any, role: str) -> bool:
    r = (role or "").strip().lower()
    if not r:
        return False
    roles = set(user_roles_list(user))
    if r in roles:
        return True
    # alias group
    if r == "student":
        return "student" in roles
    if r in {"staff", "teacher", "lecturer"}:
        return bool(roles.intersection({"staff", "teacher", "lecturer"}))
    return r in roles


def user_has_any_role(user: Any, candidates: List[str]) -> bool:
    for c in candidates:
        if user_has_role(user, c):
            return True
    return False


def user_is_system_admin(user: Any) -> bool:
    return any(r.startswith("system_") for r in user_roles_list(user))


def user_is_system_super_admin(user: Any) -> bool:
    return user_has_role(user, "system_super_admin")


def user_system_permissions_list(user: Any) -> List[str]:
    """Granted extras for SYSTEM users (e.g. database_config). system_super_admin implies all."""
    raw = getattr(user, "system_permissions", None)
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if x is not None and str(x).strip()]
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x).strip() for x in data if x is not None and str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def user_has_system_permission(user: Any, permission: str) -> bool:
    """SYSTEM users: system_super_admin has all; system_admin needs explicit grant."""
    p = (permission or "").strip()
    if not p:
        return False
    if user_is_system_super_admin(user):
        return True
    if not user_is_system_admin(user):
        return False
    return p in user_system_permissions_list(user)


def user_can_manage_other_users_passwords(user: Any) -> bool:
    """Admin, super_admin, or any system_* role may change another user's password."""
    return user_has_any_role(user, ["admin", "super_admin"]) or user_is_system_admin(user)


def user_has_assigned_role(user: Any) -> bool:
    return bool(user_roles_list(user))


def user_requires_tenant_scope_for_data(user: Any) -> bool:
    """Like legacy `user.role and not user.role.startswith('system_')` for tenant DB scoping."""
    return user_has_assigned_role(user) and not user_is_system_admin(user)


def user_is_tenant_super_admin_or_system(user: Any) -> bool:
    """Tenant super_admin or any system_* role (e.g. tenant manager routes)."""
    return user_has_role(user, "super_admin") or user_is_system_admin(user)


def primary_role(user: Any) -> str:
    """One role string for legacy UIs / routing (highest priority wins)."""
    roles = user_roles_list(user)
    if not roles:
        return ""
    order = {name: i for i, name in enumerate(_ROLE_PRIORITY)}
    roles_sorted = sorted(roles, key=lambda x: (order.get(x, 999), x))
    return roles_sorted[0]


def role_string_for_legacy(user: Any) -> str:
    """Comma-separated roles (stable order) for APIs that still expose `role` as string."""
    roles = user_roles_list(user)
    return ",".join(sorted(roles))


def role_column_contains_role(db_bind, column, role: str):
    """
    DB-specific filter: JSON array column contains `role` string.
    MySQL/MariaDB: JSON_CONTAINS. SQLite: json_each. Others: LIKE on cast.
    """
    from sqlalchemy import text
    dialect = getattr(db_bind.dialect, "name", "") or ""
    r = (role or "").strip().lower()
    quoted = json.dumps(r)
    if dialect in ("mysql", "mariadb"):
        return func.json_contains(column, quoted, "$")
    if dialect == "sqlite":
        return text(
            "EXISTS (SELECT 1 FROM json_each(users.role) WHERE json_each.value = :_role_val)"
        ).bindparams(_role_val=r)
    return func.cast(column, sa.String).like(f'%"{r}"%')


def role_column_exclude_pure_role(db_bind, column, excluded: str):
    """NOT (array length 1 AND that element is excluded)."""
    from sqlalchemy import and_, not_, text

    ex = (excluded or "").strip().lower()
    dialect = getattr(db_bind.dialect, "name", "") or ""
    if dialect in ("mysql", "mariadb"):
        return not_(
            and_(
                func.json_length(column) == 1,
                func.json_contains(column, json.dumps(ex), "$"),
            )
        )
    if dialect == "sqlite":
        return not_(
            and_(
                func.json_array_length(column) == 1,
                text(
                    "EXISTS (SELECT 1 FROM json_each(users.role) WHERE json_each.value = :_ex)"
                ).bindparams(_ex=ex),
            )
        )
    return not_(func.cast(column, sa.String) == ex)


def user_roles_exclude_pure_role(user: Any, excluded: str) -> bool:
    """True if user should be listed when excluding `excluded` (e.g. overview: non-students only)."""
    roles = user_roles_list(user)
    ex = (excluded or "").strip().lower()
    if not roles:
        return True
    if len(roles) == 1 and roles[0] == ex:
        return False
    return True
