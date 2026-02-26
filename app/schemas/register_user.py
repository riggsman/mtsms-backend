from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional


class RegisterResponse(BaseModel): 
    firstname: str
    middlename: Optional[str] = None
    lastname: str
    gender: str
    address: str
    email: EmailStr
    phone: str
    role: str
    username: str
   
    class Config:
        from_attributes = True


class RegisterRequest(BaseModel): 
    firstname: str = Field(..., min_length=1, max_length=70, description="First name is required")
    middlename: Optional[str] = Field(default=None, max_length=200, description="Middle name (optional)")
    lastname: str = Field(..., min_length=1, max_length=70, description="Last name is required")
    gender: str = Field(..., description="Gender (Male, Female, Other)")
    address: str = Field(..., min_length=1, max_length=200, description="Address is required")
    email: EmailStr = Field(..., description="Valid email address")
    phone: str = Field(..., min_length=1, max_length=200, description="Phone number is required")
    role: str = Field(..., description="User role. Registration is only available for super_admin role.")
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    tenant_name: Optional[str] = Field(default=None, description="Full tenant/school name")
    domain: Optional[str] = Field(default=None, description="Domain prefix for URLs (e.g., 'riggstech')")
    
    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v):
        allowed_genders = ['Male', 'Female', 'Other']
        if v not in allowed_genders:
            raise ValueError(f"Gender must be one of: {', '.join(allowed_genders)}")
        return v
    
    @field_validator('middlename', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty strings to None for optional fields"""
        if v is None or (isinstance(v, str) and v.strip() == ''):
            return None
        return v.strip() if isinstance(v, str) else v
    
    @field_validator('address', 'firstname', 'lastname', 'phone', 'username', mode='before')
    @classmethod
    def strip_strings(cls, v):
        """Strip whitespace from string fields"""
        if isinstance(v, str):
            return v.strip()
        return v
    
    class Config:
        # Pydantic v2 config
        str_strip_whitespace = True
