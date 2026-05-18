"""Resolve HND / DEGREE / MASTERS program type vs class year (e.g. L100, Level 200)."""
from __future__ import annotations

from typing import Any, Optional

PROGRAM_FEE_LEVELS = frozenset({"HND", "DEGREE", "MASTERS"})


def normalize_program_fee_level(raw: Optional[str]) -> Optional[str]:
    """
    Map stored values to fee-catalog level (HND, DEGREE, MASTERS).
    Returns None for class-year values like L100 or Level 200.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    u = s.upper()
    if u in {"BACHELOR", "BACHELORS"}:
        return "DEGREE"
    if u == "MASTER":
        return "MASTERS"
    if u in PROGRAM_FEE_LEVELS:
        return u
    if u.startswith("LEVEL ") or u.startswith("L") and u[1:].isdigit():
        return None
    if u.isdigit() or (len(u) <= 4 and u.replace("L", "").isdigit()):
        return None
    return None


def resolve_program_fee_level(
    student: Any,
    *,
    fee_level: Optional[str] = None,
    payment_level: Optional[str] = None,
) -> Optional[str]:
    """Pick program type for school fees / payment status (not class year)."""
    for raw in (
        getattr(student, "degree_proposed", None),
        fee_level,
        payment_level,
        getattr(student, "level", None),
    ):
        normalized = normalize_program_fee_level(raw)
        if normalized:
            return normalized
    return None


def program_level_display_label(
    student: Any,
    *,
    fee_level: Optional[str] = None,
    payment_level: Optional[str] = None,
) -> str:
    """UI label: prefer degree_proposed when it is a program type, else normalized level."""
    dp = getattr(student, "degree_proposed", None)
    if dp and normalize_program_fee_level(dp):
        return str(dp).strip().upper()
    resolved = resolve_program_fee_level(
        student, fee_level=fee_level, payment_level=payment_level
    )
    return resolved or ""
