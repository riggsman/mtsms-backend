from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class ContactRequest(BaseModel):
    """
    Payload for public contact form submissions.
    """

    name: str = Field(..., min_length=1, max_length=200, description="Sender full name")
    email: EmailStr = Field(..., description="Sender email address")
    subject: str = Field(..., min_length=1, max_length=200, description="Message subject")
    message: str = Field(..., min_length=1, description="Message body")
    phone: Optional[str] = Field(default=None, description="Optional phone number")


class ContactResponse(BaseModel):
    detail: str


class ContactMessageResponse(BaseModel):
    """
    Response model for messages stored in the system.
    Used by admin listing endpoints.
    """

    id: int
    institution_id: Optional[int] = None
    name: str
    email: str
    subject: str
    message: str
    phone: Optional[str] = None
    is_read: bool
    reply_subject: Optional[str] = None
    reply_message: Optional[str] = None
    replied_at: Optional[datetime] = None
    replied_by: Optional[str] = None
    replied_by_role: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ContactReplyRequest(BaseModel):
    """
    Payload for replying to a contact message from the admin UI.
    """

    subject: Optional[str] = Field(
        default=None,
        description="Optional custom subject for the reply. If omitted, a default will be used.",
    )
    # Accept both "message" and "reply_message" from the frontend
    message: str = Field(
        ...,
        min_length=1,
        description="Reply body content",
        alias="reply_message",
    )

    class Config:
        # Allow population by field name as well as alias,
        # so both 'message' and 'reply_message' work.
        populate_by_name = True

