from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.apis.parent_portal import child_summary, get_child_for_parent, list_children_for_parent_user
from app.dependencies.auth import require_any_role
from app.dependencies.tenantDependency import get_db
from app.models.role import UserRole
from app.models.user import User

router = APIRouter(prefix="/parent", tags=["parent-portal"])


@router.get("/children")
def list_my_children(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.PARENT)),
) -> List[Dict[str, Any]]:
    rows = list_children_for_parent_user(db, current_user)
    out: List[Dict[str, Any]] = []
    for s in rows:
        out.append(
            {
                "id": s.id,
                "student_id": s.student_id,
                "firstname": s.firstname,
                "lastname": s.lastname,
                "level": s.level,
            }
        )
    return out


@router.get("/children/{student_id}/summary")
def get_child_summary(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.PARENT)),
) -> Dict[str, Any]:
    student = get_child_for_parent(db, current_user, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found or not linked to your account",
        )
    return child_summary(db, student)
