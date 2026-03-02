from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import datetime

class UserRequest(BaseModel):
    institution_id: Optional[int] = None  # Can be None for system users
    firstname: str
    middlename: Optional[str] = None
    lastname: str
    gender: str
    address: str
    email: EmailStr
    phone: str
    username: str
    password: str
    role: str
    is_active: Optional[str] = "active"
    must_change_password: Optional[str] = "false"

class UserResponse(BaseModel):
    id: int
    institution_id: Optional[int]
    firstname: str
    middlename: Optional[str]
    lastname: str
    gender: str
    address: str
    email: str
    phone: str
    username: str
    role: str
    user_type: str
    is_active: str
    must_change_password: Optional[str] = "false"
    profile_picture: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode='before')
    @classmethod
    def validate_datetime_fields(cls, data):
        """Handle invalid MySQL datetime values like '0000-00-00 00:00:00'"""
        if isinstance(data, dict):
            # Handle created_at
            if 'created_at' in data:
                created_at = data['created_at']
                # Check for invalid datetime strings or datetime objects with invalid dates
                if created_at is None:
                    data['created_at'] = None
                elif isinstance(created_at, str) and (created_at.startswith('0000-00-00') or created_at == '0000-00-00 00:00:00'):
                    data['created_at'] = None
                elif hasattr(created_at, 'year') and created_at.year == 0:
                    # Handle datetime object with year 0
                    data['created_at'] = None
                elif created_at is not None and not isinstance(created_at, datetime):
                    try:
                        # Try to parse if it's a valid datetime string
                        if isinstance(created_at, str) and not created_at.startswith('0000-00-00'):
                            parsed = datetime.fromisoformat(created_at.replace(' ', 'T'))
                            # Check if parsed datetime is valid
                            if parsed.year == 0:
                                data['created_at'] = None
                            else:
                                data['created_at'] = parsed
                    except (ValueError, AttributeError, TypeError):
                        data['created_at'] = None
            
            # Handle updated_at
            if 'updated_at' in data:
                updated_at = data['updated_at']
                # Check for invalid datetime strings or datetime objects with invalid dates
                if updated_at is None:
                    data['updated_at'] = None
                elif isinstance(updated_at, str) and (updated_at.startswith('0000-00-00') or updated_at == '0000-00-00 00:00:00'):
                    data['updated_at'] = None
                elif hasattr(updated_at, 'year') and updated_at.year == 0:
                    # Handle datetime object with year 0
                    data['updated_at'] = None
                elif updated_at is not None and not isinstance(updated_at, datetime):
                    try:
                        # Try to parse if it's a valid datetime string
                        if isinstance(updated_at, str) and not updated_at.startswith('0000-00-00'):
                            parsed = datetime.fromisoformat(updated_at.replace(' ', 'T'))
                            # Check if parsed datetime is valid
                            if parsed.year == 0:
                                data['updated_at'] = None
                            else:
                                data['updated_at'] = parsed
                    except (ValueError, AttributeError, TypeError):
                        data['updated_at'] = None
        elif hasattr(data, '__dict__'):
            # Handle SQLAlchemy model objects
            if hasattr(data, 'created_at') and data.created_at is not None:
                if hasattr(data.created_at, 'year') and data.created_at.year == 0:
                    data.created_at = None
                elif isinstance(data.created_at, str) and data.created_at.startswith('0000-00-00'):
                    data.created_at = None
            if hasattr(data, 'updated_at') and data.updated_at is not None:
                if hasattr(data.updated_at, 'year') and data.updated_at.year == 0:
                    data.updated_at = None
                elif isinstance(data.updated_at, str) and data.updated_at.startswith('0000-00-00'):
                    data.updated_at = None
        return data

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    firstname: Optional[str] = None
    middlename: Optional[str] = None
    lastname: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    user_type: Optional[str] = None
    is_active: Optional[str] = None
    must_change_password: Optional[str] = None

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
