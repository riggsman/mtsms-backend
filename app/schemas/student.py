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
    department_id: int
    academic_year_id: int
    guardian_id: int
    photo: Optional[str] = None  # Base64 encoded photo or photo URL
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
    department_id: int
    academic_year_id: int
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
    photo: Optional[str] = None  # Base64 encoded photo (data:image/...;base64,... format)

class StudentUpdate(BaseModel):
    firstname: Optional[str] = None
    middlename: Optional[str] = None
    lastname: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    class_id: Optional[int] = None
    department_id: Optional[int] = None
    academic_year_id: Optional[int] = None
    guardian_id: Optional[int] = None
    photo: Optional[str] = None  # Base64 encoded photo (data:image/...;base64,... format)


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