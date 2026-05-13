from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class CommunicationBase(BaseModel):
    channel: str
    subject: Optional[str] = None
    content: str
    recipient_type: str
    recipient_filter: Optional[Dict[str, Any]] = None

class CommunicationCreate(CommunicationBase):
    pass

class CommunicationResponse(CommunicationBase):
    id: int
    institution_id: int
    sender_id: int
    total_recipients: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class CommunicationTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    subject_template: Optional[str] = None
    content_template: str
    category: Optional[str] = None
    variables: Optional[List[str]] = None

class CommunicationTemplateCreate(CommunicationTemplateBase):
    pass

class CommunicationTemplateResponse(CommunicationTemplateBase):
    id: int
    institution_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class CircularBase(BaseModel):
    title: str
    content: str
    attachment_path: Optional[str] = None
    target_audience: Optional[List[str]] = None
    expiry_date: Optional[datetime] = None

class CircularCreate(CircularBase):
    pass

class CircularResponse(CircularBase):
    id: int
    institution_id: int
    posted_by: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
