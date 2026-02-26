from pydantic import BaseModel
from sqlalchemy import DateTime
from typing import Optional

class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    role: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    tenantName: Optional[str] = None
    domain: Optional[str] = None
    institution_id: Optional[int] = None
    mustChangePassword: Optional[bool] = False
    
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