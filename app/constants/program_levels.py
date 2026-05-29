"""Degree / program level codes for tenant configuration and student registration."""

from __future__ import annotations

from typing import List, Optional, Sequence

ALL_PROGRAM_LEVEL_CODES: List[str] = [
    "HND",
    "BTECH",
    "BSC",
    "MTECH",
    "MSC",
    "MBA",
]

DEFAULT_ENABLED_PROGRAM_LEVELS: List[str] = list(ALL_PROGRAM_LEVEL_CODES)


def normalize_program_level_code(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    code = str(raw).strip().upper()
    if not code:
        return None
    # Legacy aliases still stored on some students
    legacy = {
        "BACHELOR": "BSC",
        "BACHELORS": "BSC",
        "DEGREE": "BSC",
        "MASTER": "MSC",
        "MASTERS": "MSC",
    }
    if code in legacy:
        return legacy[code]
    if code in ALL_PROGRAM_LEVEL_CODES:
        return code
    return None


def sanitize_enabled_program_levels(
    values: Optional[Sequence[str]],
    *,
    default_all: bool = True,
) -> List[str]:
    if values is None:
        return list(DEFAULT_ENABLED_PROGRAM_LEVELS) if default_all else []
    out: List[str] = []
    seen = set()
    for item in values:
        code = normalize_program_level_code(item)
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    if not out and default_all:
        return list(DEFAULT_ENABLED_PROGRAM_LEVELS)
    return out
