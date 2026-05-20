from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional, List, Union, Any
from datetime import datetime


class UserRequest(BaseModel):
    institution_id: Optional[int] = None  # Can be None for system users
    branch_id: Optional[int] = None  # Campus when branches are enabled
    department_id: Optional[int] = None
    position: Optional[str] = None
    designation: Optional[str] = None
    title: Optional[str] = None
    firstname: str
    middlename: Optional[str] = None
    lastname: str
    gender: str
    address: str
    email: EmailStr
    phone: str
    username: str
    password: str
    role: Union[str, List[str]]
    is_active: Optional[str] = "active"
    must_change_password: Optional[str] = "false"

    @field_validator("role", mode="before")
    @classmethod
    def coerce_role_input(cls, v: Any):
        if v is None:
            return v
        if isinstance(v, list):
            return v
        return str(v).strip()


class UserResponse(BaseModel):
    id: int
    institution_id: Optional[int]
    department_id: Optional[int] = None
    position: Optional[str] = None
    designation: Optional[str] = None
    title: Optional[str] = None
    firstname: str
    middlename: Optional[str]
    lastname: str
    gender: str
    address: str
    email: str
    phone: str
    username: str
    roles: List[str]
    role: str  # legacy: comma-separated, sorted
    user_type: str
    is_active: str
    must_change_password: Optional[str] = "false"
    profile_picture: Optional[str] = None
    language: Optional[str] = "en"
    branch_id: Optional[int] = None
    system_permissions: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def prepare_user_response(cls, data: Any):
        """ORM -> dict, fix MySQL zero dates, normalize roles."""
        from sqlalchemy import inspect as sa_inspect
        from app.helpers.user_roles import parse_roles_to_list, user_system_permissions_list

        if data is not None and not isinstance(data, dict):
            try:
                insp = sa_inspect(data)
                if insp.mapper:
                    data = {attr.key: getattr(data, attr.key) for attr in insp.mapper.column_attrs}
            except Exception:
                pass

        if isinstance(data, dict):
            # Handle invalid MySQL datetime values like '0000-00-00 00:00:00'
            if "created_at" in data:
                created_at = data["created_at"]
                if created_at is None:
                    data["created_at"] = None
                elif isinstance(created_at, str) and (
                    created_at.startswith("0000-00-00") or created_at == "0000-00-00 00:00:00"
                ):
                    data["created_at"] = None
                elif hasattr(created_at, "year") and created_at.year == 0:
                    data["created_at"] = None
                elif created_at is not None and not isinstance(created_at, datetime):
                    try:
                        if isinstance(created_at, str) and not created_at.startswith("0000-00-00"):
                            parsed = datetime.fromisoformat(created_at.replace(" ", "T"))
                            data["created_at"] = None if parsed.year == 0 else parsed
                    except (ValueError, AttributeError, TypeError):
                        data["created_at"] = None

            if "updated_at" in data:
                updated_at = data["updated_at"]
                if updated_at is None:
                    data["updated_at"] = None
                elif isinstance(updated_at, str) and (
                    updated_at.startswith("0000-00-00") or updated_at == "0000-00-00 00:00:00"
                ):
                    data["updated_at"] = None
                elif hasattr(updated_at, "year") and updated_at.year == 0:
                    data["updated_at"] = None
                elif updated_at is not None and not isinstance(updated_at, datetime):
                    try:
                        if isinstance(updated_at, str) and not updated_at.startswith("0000-00-00"):
                            parsed = datetime.fromisoformat(updated_at.replace(" ", "T"))
                            data["updated_at"] = None if parsed.year == 0 else parsed
                    except (ValueError, AttributeError, TypeError):
                        data["updated_at"] = None

            rl = data.get("roles")
            if rl is None:
                rl = parse_roles_to_list(data.get("role"))
            elif not isinstance(rl, list):
                rl = parse_roles_to_list(rl)
            data["roles"] = rl
            data["role"] = ",".join(sorted(rl))
            data["system_permissions"] = user_system_permissions_list(data)

        return data

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    institution_id: Optional[int] = None
    department_id: Optional[int] = None
    position: Optional[str] = None
    designation: Optional[str] = None
    title: Optional[str] = None
    firstname: Optional[str] = None
    middlename: Optional[str] = None
    lastname: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[Union[str, List[str]]] = None
    user_type: Optional[str] = None
    is_active: Optional[str] = None
    must_change_password: Optional[str] = None
    language: Optional[str] = None
    branch_id: Optional[int] = None

    @field_validator("role", mode="before")
    @classmethod
    def coerce_role_update(cls, v: Any):
        if v is None:
            return v
        if isinstance(v, list):
            return v
        return str(v).strip()


class StudentPasswordAssign(BaseModel):
    student_id: int
    password: str
    username: Optional[str] = None  # If not provided, will use email or student_id


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class SuspendUserRequest(BaseModel):
    reason: str  # Required reason for suspension
    student_id: Optional[int] = None  # Optional: if provided, will suspend by student_id instead of user_id
