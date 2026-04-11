import enum
from typing import List, Optional


class InstitutionCategory(str, enum.Enum):
    """Institution category enumeration"""
    HI = "HI"
    SI = "SI"

class InstitutionType(str, enum.Enum):
    """Institution type enumeration"""
    SCHOOL = "SCHOOL"
    UNIVERSITY = "UNIVERSITY"
    COLLEGE = "COLLEGE"

class StudentCategory(str, enum.Enum):
    """Student category enumeration"""
    UNDERGRADUATE = "Undergraduate"
    GRADUATE = "Graduate"
    POST_GRADUATE = "Post-Graduate"

class StudentLevel(str, enum.Enum):
    """Student level enumeration"""
    MASTERS = "MASTERS"
    BACHELOR = "BACHELOR"
    BBA = "Bachelor of Business Administration"
    MBA = "Master of Business Administration"
    MS = "Master of Science"
   