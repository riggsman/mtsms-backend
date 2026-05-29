from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.classes import Class
from app.models.user import User


SYSTEM_DEFAULT_INSTITUTION_ID = 0


def _default_classes_payload() -> List[Dict]:
    payload: List[Dict] = []

    hi_classes = [
        ("Level 100", "L100", "HI", "HI", False),
        ("Level 200", "L200", "HI", "HI", False),
        ("Level 300", "L300", "HI", "HI", False),
        ("Level 400", "L400", "HI", "HI", False),
    ]
    si_classes = [
        ("Form 1", "F1", "SI", "SI", True),
        ("Form 2", "F2", "SI", "SI", True),
        ("Form 3", "F3", "SI", "SI", True),
        ("Form 4", "F4", "SI", "SI", True),
        ("Form 5", "F5", "SI", "SI", True),
        ("Lower Sixth", "L6", "SI", "SI", True),
        ("Upper Sixth", "U6", "SI", "SI", True),
    ]

    for name, code, institution_level, category, is_custom in hi_classes + si_classes:
        payload.append(
            {
                "institution_id": SYSTEM_DEFAULT_INSTITUTION_ID,
                "name": name,
                "code": code,
                "institution_level": institution_level,
                "category": category,
                "is_custom": is_custom,
                "created_at": datetime.utcnow(),
            }
        )
    return payload


def seed_default_classes(session: Session, force: bool = False):
    """
    Seed default classes for HI and SI.
    Runs only once unless force=True.
    """
    defaults = _default_classes_payload()
    existing = (
        session.query(Class)
        .filter(Class.institution_id == SYSTEM_DEFAULT_INSTITUTION_ID, Class.deleted_at.is_(None))
        .all()
    )
    existing_by_code = {str(item.code).upper().strip(): item for item in existing if item.code}

    to_insert: List[Dict] = []
    to_update = 0
    for row in defaults:
        code_key = str(row["code"]).upper().strip()
        current = existing_by_code.get(code_key)
        if not current:
            to_insert.append(row)
            continue
        if force:
            current.name = row["name"]
            current.institution_level = row["institution_level"]
            current.category = row["category"]
            current.is_custom = row["is_custom"]
            current.updated_at = datetime.utcnow()
            to_update += 1

    if to_insert:
        session.bulk_insert_mappings(Class, to_insert)
    if to_insert or to_update:
        session.commit()
        print(f"Seeded default classes: inserted={len(to_insert)}, updated={to_update}")
    else:
        print("Default classes already seeded and up-to-date.")


def seed_default_admin_user(session: Session, force: bool = False):
    """
    Seed default system super admin user.
    Runs only once unless force=True.
    """
    from app.authentication.authenticator import verify_password, hash_password
    adminPass = hash_password("systemadmin")
    default_user = {
        "institution_id": None,
        "branch_id": None,
        "department_id": None,
        "position": "System Administrator",
        "firstname": "System",
        "middlename": None,
        "lastname": "Admin",
        "gender": "male",
        "address": "System Address",
        "email": "system@admin.com",
        "phone": "+237688776677",
        "username": "systemadmin",
        "password": adminPass,
        "role": ["system_super_admin"],
        "user_type": "SYSTEM",
        "is_active": "active",
        "must_change_password": "false",
        "profile_picture": None,
        "language": "en",
        "created_at": datetime.utcnow(),
    }
    existing = session.query(User).filter(User.email == default_user["email"]).first()
    if not existing:
        session.add(User(**default_user))
        session.commit()
        print("Seeded default system admin user.")
        return

    if force:
        existing.firstname = default_user["firstname"]
        existing.lastname = default_user["lastname"]
        existing.username = default_user["username"]
        existing.role = default_user["role"]
        existing.user_type = default_user["user_type"]
        existing.is_active = default_user["is_active"]
        existing.gender = default_user["gender"]
        existing.address = default_user["address"]
        existing.phone = default_user["phone"]
        existing.language = default_user["language"]
        # Keep existing password unless explicitly forced
        existing.updated_at = datetime.utcnow()
        session.commit()
        print("Updated default system admin user.")
    else:
        print("Default system admin user already seeded.")

