from pydantic import BaseModel

from typing import Optional
from datetime import datetime

class StudentResponse(BaseModel):
    id: int
    institution_id: int
    firstname: str
    middlename: Optional[str]
    lastname: str
    dob: str
    gender: str
    address: str
    email: str
    phone: str
    student_id: str
    class_id: int
    level: str
    department_id: int
    specialization_id: Optional[int] = None  # Department from specializations table
    school_id: int
    academic_year_id: int
    guardian_id: int
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_address: Optional[str] = None
    guardian_relationship: Optional[str] = None
    guardian_gender: Optional[str] = None
    guardian_email: Optional[str] = None
    guardian_occupation: Optional[str] = None
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    place_of_birth: Optional[str] = None
    degree_proposed: Optional[str] = None
    class_name: Optional[str] = None
    department_name: Optional[str] = None
    specialization_name: Optional[str] = None
    school_name: Optional[str] = None
    photo: Optional[str] = None  # Photo file path (accepts base64 for upload, stores relative path)
    created_at: datetime
    updated_at: Optional[datetime]

class StudentRequest(BaseModel):
    firstname: str
    middlename: Optional[str] = None
    lastname: str
    dob: str
    gender: str
    address: str
    email: str
    phone: str
    student_id: str
    class_id: int
    level: str
    department_id: int  # School (from departments table)
    specialization_id: Optional[int] = None  # Department (from specializations table)
    school_id: int
    academic_year_id: int
    branch_id: Optional[int] = None
    institution_id: Optional[int] = None  # Optional - can be provided in request body or will use current_user.institution_id
    guardian_id: Optional[int] = None  # Optional - will be created if guardian_info is provided
    # Guardian information (optional - if provided, guardian will be created)
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_address: Optional[str] = None
    guardian_relationship: Optional[str] = None
    guardian_gender: Optional[str] = None
    guardian_email: Optional[str] = None
    guardian_occupation: Optional[str] = None
    photo: Optional[str] = None  # Accepts base64 encoded photo (data:image/...;base64,...), stores file path
    place_of_birth: Optional[str] = None  # Student's place of birth
    degree_proposed: Optional[str] = None  # Degree program being enrolled

class StudentUpdate(BaseModel):
    firstname: Optional[str] = None
    middlename: Optional[str] = None
    lastname: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    student_id: Optional[str] = None  # Registration/matricule (when allowed to change)
    class_id: Optional[int] = None
    level: Optional[str] = None  # HND, DEGREE, MASTERS, etc.
    school_id: Optional[int] = None
    department_id: Optional[int] = None  # School (from departments table)
    specialization_id: Optional[int] = None  # Department (from specializations table)
    academic_year_id: Optional[int] = None
    guardian_id: Optional[int] = None
    branch_id: Optional[int] = None
    photo: Optional[str] = None  # Accepts base64 encoded photo (data:image/...;base64,...), stores file path
    place_of_birth: Optional[str] = None  # Student's place of birth
    degree_proposed: Optional[str] = None  # Degree program being enrolled


class GuardianRequest(BaseModel):
    guardian_name:str
    phone:str
    address:str
    relationship:str
    gender:str

class GuardianResponse(BaseModel):
    id:int
    guardian_name:str
    phone:str
    address:str
    relationship:str
    gender:str

    class Config:
        from_attributes = True