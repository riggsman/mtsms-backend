from enum import Enum

class UserRole(str, Enum):
    """User role enumeration. Teaching access uses STAFF (canonical); 'lecturer' is legacy in DB only."""
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"
    STAFF = "staff"
    # Same value as STAFF — teaching/staff login; kept for code that referenced LECTURER
    LECTURER = "staff"
    SUPER_ADMIN = "super_admin"
    SECRETARY = "secretary"
    SYSTEM_ADMIN = "system_admin"
    SYSTEM_SUPER_ADMIN = "system_super_admin"
    
    @classmethod
    def has_value(cls, value: str) -> bool:
        """Check if a value is a valid role (accepts legacy 'lecturer' as staff)."""
        if not value:
            return False
        v = str(value).strip().lower()
        if v == "lecturer":
            v = "staff"
        return v in {role.value for role in cls}
    
    @classmethod
    def get_all_roles(cls) -> list[str]:
        """Distinct role string values"""
        return sorted({role.value for role in cls})
