from enum import Enum

class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"
    STAFF = "staff"
    SUPER_ADMIN = "super_admin"
    SECRETARY = "secretary"
    
    @classmethod
    def has_value(cls, value: str) -> bool:
        """Check if a value is a valid role"""
        return value in [role.value for role in cls]
    
    @classmethod
    def get_all_roles(cls) -> list[str]:
        """Get all role values"""
        return [role.value for role in cls]
