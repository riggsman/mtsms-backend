from datetime import datetime
from email.mime import text
from app.models.classes import Class
from sqlalchemy import event
from sqlalchemy.orm import Session


# def insert_default_classes(target, connection, **kw):
#     """Insert default classes for HI and SI after table creation.
#        Skips if data already exists.
#     """
#     # Check if defaults already exist to make it idempotent
#     result = connection.execute(
#         text("SELECT COUNT(*) FROM classes WHERE is_custom = false")
#     ).scalar()
    
#     if result > 0:
#         return  # Defaults already present

#     defaults = []

#     # Higher Institution (HI) defaults
#     hi_classes = [
#         {"name": "Level 100", "code": "L100", "institution_level": "HI", "category": "Undergraduate"},
#         {"name": "Level 200", "code": "L200", "institution_level": "HI", "category": "Undergraduate"},
#         {"name": "Level 300", "code": "L300", "institution_level": "HI", "category": "Undergraduate"},
#         {"name": "Level 400", "code": "L400", "institution_level": "HI", "category": "Undergraduate"},
#     ]
#     for cls in hi_classes:
#         defaults.append({
#             **cls,
#             "institution_id": 0,      # Use 0 or a sentinel value for global defaults
#             "is_custom": False,
#             "level_id": None,
#             "department_id": None,
#             "academic_year_id": None,
#             "capacity": None,
#             "created_at": datetime.datetime.utcnow(),
#         })

#     # Secondary Institution (SI) defaults
#     si_classes = [
#         {"name": "Form 1", "code": "F1", "institution_level": "SI", "category": "Secondary"},
#         {"name": "Form 2", "code": "F2", "institution_level": "SI", "category": "Secondary"},
#         {"name": "Form 3", "code": "F3", "institution_level": "SI", "category": "Secondary"},
#         {"name": "Form 4", "code": "F4", "institution_level": "SI", "category": "Secondary"},
#         {"name": "Form 5", "code": "F5", "institution_level": "SI", "category": "Secondary"},
#         {"name": "Lower Sixth", "code": "L6", "institution_level": "SI", "category": "Advanced"},
#         {"name": "Upper Sixth", "code": "U6", "institution_level": "SI", "category": "Advanced"},
#     ]
#     for cls in si_classes:
#         defaults.append({
#             **cls,
#             "institution_id": 0,
#             "is_custom": False,
#             "level_id": None,
#             "department_id": None,
#             "academic_year_id": None,
#             "capacity": None,
#             "created_at": datetime.datetime.utcnow(),
#         })

#     # Bulk insert using Core for efficiency and to avoid ORM session issues
#     if defaults:
#         connection.execute(Class.__table__.insert(), defaults)


# # Attach the event listener to the table
# event.listen(Class.__table__, 'after_create', insert_default_classes)




def seed_default_classes(session: Session, force: bool = False):
    """
    Seed default classes for HI and SI.
    Runs only once unless force=True.
    """
    # Check if defaults already exist
    if not force:
        count = session.query(Class).filter(Class.is_custom == False).count()
        if count > 0:
            print("Default classes already seeded.")
            return

    print("Seeding default classes...")

    defaults = []

    # Higher Institution (HI) - Levels 100 to 400
    hi_classes = [
        ("Level 100", "L100", "HI", "HI"),
        ("Level 200", "L200", "HI", "HI"),
        ("Level 300", "L300", "HI", "HI"),
        ("Level 400", "L400", "HI", "HI"),
    ]
    for name, code, inst_level, cat in hi_classes:
        defaults.append({
            "institution_id": 0,           # Sentinel value for system defaults
            "name": name,
            "code": code,
            "institution_level": inst_level,
            "category": cat,
            "is_custom": False,
            "created_at": datetime.now(),
        })

    # Secondary Institution (SI)
    si_classes = [
        ("Form 1", "F1", "SI", "SI"),
        ("Form 2", "F2", "SI", "SI"),
        ("Form 3", "F3", "SI", "SI"),
        ("Form 4", "F4", "SI", "SI"),
        ("Form 5", "F5", "SI", "SI"),
        ("Lower Sixth", "L6", "SI", "SI"),
        ("Upper Sixth", "U6", "SI", "SI"),
    ]
    for name, code, inst_level, cat in si_classes:
        defaults.append({
            "institution_id": 0,
            "name": name,
            "code": code,
            "institution_level": inst_level,
            "category": cat,
            "is_custom": True,
            "created_at": datetime.now(),
        })

    # Bulk insert
    if defaults:
        session.bulk_insert_mappings(Class, defaults)
        session.commit()
        print(f"Successfully seeded {len(defaults)} default classes.")
    else:
        print("No defaults to seed.")