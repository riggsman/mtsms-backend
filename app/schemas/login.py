from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy import DateTime
from typing import Optional, List, Any

class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    roles: List[str]
    role: str  # legacy comma-separated (sorted)
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    tenantName: Optional[str] = None
    domain: Optional[str] = None
    institution_id: Optional[int] = None
    mustChangePassword: Optional[bool] = False
    language: Optional[str] = "en"
    # Extra capabilities for SYSTEM users (e.g. database_config)
    system_permissions: Optional[List[str]] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_roles(cls, data: Any):
        from app.helpers.user_roles import parse_roles_to_list, role_string_for_legacy
        if isinstance(data, dict):
            if data.get("roles") is not None:
                rl = data["roles"] if isinstance(data["roles"], list) else parse_roles_to_list(data["roles"])
            else:
                rl = parse_roles_to_list(data.get("role"))
            data["roles"] = rl
            data["role"] = ",".join(sorted(rl))
            return data
        return data

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role_field(cls, v):
        if v is None:
            return v
        from app.helpers.role_normalization import normalize_user_role_string
        out = normalize_user_role_string(str(v))
        return out if out else str(v)
    
    class Config:
        from_attributes = True

class LoginResponse(BaseModel): 
    access_token: str
    refresh_token: str
    token_type: str
    user: Optional[UserInfo] = None
    tenantName: Optional[str] = None
    domain: Optional[str] = None
   
  

class LoginRequest(BaseModel): 
    username: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginOtpRequest(BaseModel):
    email: str


class LoginOtpVerifyRequest(BaseModel):
    email: str
    otp: str


class LoginOtpRequestResponse(BaseModel):
    message: str
