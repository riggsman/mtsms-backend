from __future__ import annotations

from app.models.department import Department
from app.models.course import Course


def ensure_department(db, institution_id: int = 1, code: str = "DPT100", name: str = "Dept 100") -> Department:
    d = db.query(Department).filter(Department.code == code, Department.deleted_at.is_(None)).first()
    if d:
        return d
    d = Department(institution_id=institution_id, name=name, code=code)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def ensure_course(db, institution_id: int = 1, code: str = "CRS100", name: str = "Course 100") -> Course:
    c = db.query(Course).filter(Course.code == code, Course.deleted_at.is_(None)).first()
    if c:
        return c
    d = ensure_department(db, institution_id=institution_id)
    c = Course(institution_id=institution_id, name=name, code=code, department_id=d.id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c
