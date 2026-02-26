from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TeacherRequest(BaseModel):
    firstname: str
    middlename: Optional[str] = None
    lastname: str
    dob: str
    gender: str
    address: str
    email: str
    phone: str
    department_id: int
    employee_id: str
    qualification: Optional[str] = None
    specialization: Optional[str] = None
    institution_id: Optional[int] = None  # For tenant isolation

class TeacherResponse(BaseModel):
    id: int
    institution_id: int  # For tenant isolation
    firstname: str
    middlename: Optional[str]
    lastname: str
    dob: str
    gender: str
    address: str
    email: str
    phone: str
    department_id: int
    employee_id: str
    qualification: Optional[str]
    specialization: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class TeacherUpdate(BaseModel):
    firstname: Optional[str] = None
    middlename: Optional[str] = None
    lastname: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    qualification: Optional[str] = None
    specialization: Optional[str] = None