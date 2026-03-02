from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime

class SystemConfigBase(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None

class SystemConfigCreate(SystemConfigBase):
    pass

class SystemConfigUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None

class SystemConfigResponse(SystemConfigBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class DatabaseModeResponse(BaseModel):
    mode: str  # 'shared' or 'multi_tenant'
    description: str

class DatabaseModeUpdate(BaseModel):
    mode: str  # 'shared' or 'multi_tenant'


class NotificationAdminEmail(BaseModel):
    """Single notification admin email configuration"""
    email: EmailStr
    enabled: bool = True


class NotificationAdminEmailsConfig(BaseModel):
    """
    Configuration for system admin notification emails.
    Supports up to 3 emails, each with an enabled flag.
    """
    emails: List[NotificationAdminEmail]

    @field_validator("emails")
    @classmethod
    def validate_email_count(cls, v: List[NotificationAdminEmail]) -> List[NotificationAdminEmail]:
        if len(v) > 3:
            raise ValueError("A maximum of 3 notification admin emails is allowed")
        return v
