"""
HI (higher institution) application-level class rows: tied to degree program codes.

Seeded per institution so "Level applying for" can be filtered server-side by category (HI)
and degree program (HND/BSC → Level 1–3; MTECH/MBA/MSC → Masters 1–2; BTECH → single placeholder).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from app.models.classes import Class

# Canonical codes stored in students.degree_proposed / tenant program levels
APPLICATION_LEVEL_SEED: List[dict] = [
    {"name": "Level 1", "code": "LEVEL_1", "degree_program_codes": ["HND", "BSC"]},
    {"name": "Level 2", "code": "LEVEL_2", "degree_program_codes": ["HND", "BSC"]},
    {"name": "Level 3", "code": "LEVEL_3", "degree_program_codes": ["HND", "BSC"]},
    {"name": "Masters 1", "code": "MASTERS_1", "degree_program_codes": ["MTECH", "MBA", "MSC"]},
    {"name": "Masters 2", "code": "MASTERS_2", "degree_program_codes": ["MTECH", "MBA", "MSC"]},
    # B.Tech has no year split in this model; one placeholder row satisfies NOT NULL class_id on students.
    {"name": "B.Tech (no class year)", "code": "BTECH_COHORT", "degree_program_codes": ["BTECH"]},
]


def normalize_degree_program_code(raw: Optional[str]) -> Optional[str]:
    if raw is None or str(raw).strip() == "":
        return None
    u = str(raw).strip().upper()
    aliases = {
        "BACHELOR": "BSC",
        "BACHELORS": "BSC",
        "DEGREE": "BSC",
        "MASTER": "MSC",
        "MASTERS": "MSC",
    }
    return aliases.get(u, u)


def seed_hi_application_level_classes(db: Session, institution_id: int) -> int:
    """
    Insert default HI application-level rows for one institution if missing (by code).
    Returns number of rows inserted.
    """
    if not institution_id:
        return 0
    existing = (
        db.query(Class)
        .filter(Class.institution_id == institution_id, Class.deleted_at.is_(None))
        .all()
    )
    existing_codes = {str(c.code).upper().strip() for c in existing if c.code}
    inserted = 0
    now = datetime.utcnow()
    for row in APPLICATION_LEVEL_SEED:
        code_key = str(row["code"]).upper().strip()
        if code_key in existing_codes:
            continue
        db.add(
            Class(
                institution_id=institution_id,
                name=row["name"],
                code=row["code"],
                institution_level="HI",
                category="HI",
                is_custom=True,
                degree_program_codes=list(row["degree_program_codes"]),
                created_at=now,
            )
        )
        inserted += 1
        existing_codes.add(code_key)
    if inserted:
        db.commit()
    return inserted


def filter_classes_by_degree_program(
    classes: List[Any],
    degree_program: Optional[str],
    institution_level: Optional[str],
) -> List[Any]:
    """When listing HI classes for registration, only return rows whose degree_program_codes contains the program."""
    if not degree_program or (institution_level or "").upper() != "HI":
        return list(classes)
    want = normalize_degree_program_code(degree_program)
    if not want:
        return list(classes)
    out: List[Any] = []
    for c in classes:
        codes = getattr(c, "degree_program_codes", None)
        if not codes or not isinstance(codes, (list, tuple)):
            continue
        normalized = {normalize_degree_program_code(x) for x in codes if x is not None}
        normalized.discard(None)
        if want in normalized:
            out.append(c)
    return out
