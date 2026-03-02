from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.contact import (
    ContactRequest,
    ContactResponse,
    ContactMessageResponse,
    ContactReplyRequest,
)
from app.services.email_service import EmailService
from app.helpers.async_helper import run_async_safe
from app.conf.config import settings
from app.database.base import get_db_session
from app.dependencies.auth import require_any_role_admin
from app.models.user import User
from app.models.role import UserRole
from app.models.contact_message import ContactMessage
from app.helpers.pagination import PaginatedResponse


contact = APIRouter()


@contact.post("/contact", response_model=ContactResponse)
async def submit_contact_form(
    payload: ContactRequest,
    db: Session = Depends(get_db_session),
):
    """
    Public contact endpoint.

    - Accepts name, email, subject, message, optional phone
    - Stores the message in the tenant database
    - Sends an acknowledgement email back to the sender
    """
    # Store contact message
    contact_message = ContactMessage(
        institution_id=None,
        name=payload.name,
        email=str(payload.email),
        subject=payload.subject,
        message=payload.message,
        phone=payload.phone,
        is_read=False,
    )

    db.add(contact_message)
    db.commit()
    db.refresh(contact_message)

    # Build acknowledgement email to sender
    # Default to EduSphere if APP_NAME is not set in configuration
    app_name = getattr(settings, "APP_NAME", "EduSphere")

    subject = f"Thank you for contacting {app_name}"

    phone_block = f"<p><strong>Phone:</strong> {payload.phone}</p>" if payload.phone else ""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            .details {{ background-color: #fff; padding: 15px; border-left: 4px solid #4CAF50; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Thank You for Reaching Out</h1>
            </div>
            <div class="content">
                <p>Dear {payload.name},</p>
                <p>We have received your message and our team will review it and get back to you as soon as possible.</p>
                <div class="details">
                    <h3>Your Message Details</h3>
                    <p><strong>Subject:</strong> {payload.subject}</p>
                    <p><strong>Email:</strong> {payload.email}</p>
                    {phone_block}
                    <p><strong>Message:</strong></p>
                    <p>{payload.message}</p>
                </div>
                <p>If this was not you, you can safely ignore this email.</p>
            </div>
            <div class="footer">
                <p>This is an automated acknowledgement from {app_name}. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
Thank you for contacting {app_name}

Dear {payload.name},

We have received your message and our team will review it and get back to you as soon as possible.

Subject: {payload.subject}
Email: {payload.email}
{"Phone: " + payload.phone if payload.phone else ""}

Message:
{payload.message}

This is an automated acknowledgement from {app_name}. Please do not reply to this email.
""".strip()

    # Fire-and-forget sending (non-blocking for the API)
    run_async_safe(
        EmailService.send_email(
            to_email=str(payload.email),
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
    )

    return ContactResponse(detail="Message received. A confirmation email has been sent if email delivery is enabled.")


@contact.get(
    "/admin/contact-messages",
    response_model=PaginatedResponse[ContactMessageResponse],
)
def list_contact_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    only_unread: bool = Query(False),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(
        require_any_role_admin(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN, UserRole.SECRETARY)
    ),
):
    """
    List contact messages (global admin view), paginated.
    Admin/staff/secretary roles only (using global database, no tenant header required).
    """
    query = db.query(ContactMessage).filter(ContactMessage.deleted_at.is_(None))

    if only_unread:
        query = query.filter(ContactMessage.is_read.is_(False))

    total = query.count()
    messages = (
        query.order_by(ContactMessage.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Mark fetched messages as read if we are not filtering only_unread
    if not only_unread and messages:
        for msg in messages:
            if not msg.is_read:
                msg.is_read = True
        db.commit()

    return PaginatedResponse.create(
        items=[ContactMessageResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
    )


@contact.get("/admin/contact-messages/unread-count")
def get_unread_contact_messages_count(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(
        require_any_role_admin(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN, UserRole.SECRETARY)
    ),
):
    """
    Get the count of unread contact messages.
    """
    count = (
        db.query(ContactMessage)
        .filter(
            ContactMessage.deleted_at.is_(None),
            ContactMessage.is_read.is_(False),
        )
        .count()
    )

    return {"unread_count": count}


@contact.patch("/admin/contact-messages/{message_id}/read")
def mark_contact_message_read(
    message_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(
        require_any_role_admin(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN, UserRole.SECRETARY)
    ),
):
    """
    Mark a specific contact message as read.
    """
    message = (
        db.query(ContactMessage)
        .filter(
            ContactMessage.id == message_id,
            ContactMessage.deleted_at.is_(None),
        )
        .first()
    )

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact message not found",
        )

    if not message.is_read:
        message.is_read = True
        db.commit()
        db.refresh(message)

    return {"detail": "Contact message marked as read", "id": message.id, "is_read": message.is_read}


@contact.patch("/admin/contact-messages/{message_id}/reply")
def reply_to_contact_message(
    message_id: int,
    payload: ContactReplyRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(
        require_any_role_admin(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN, UserRole.SECRETARY)
    ),
):
    """
    Reply to a contact message by sending an email back to the client.
    """
    message = (
        db.query(ContactMessage)
        .filter(
            ContactMessage.id == message_id,
            ContactMessage.deleted_at.is_(None),
        )
        .first()
    )

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact message not found",
        )

    app_name = getattr(settings, "APP_NAME", "EduSphere")

    # Build subject: use custom if provided, else default referencing original subject
    subject = (
        payload.subject
        if payload.subject
        else f"Re: {message.subject} - {app_name} Support"
    )

    # Basic HTML reply content including original message context
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .original {{ margin-top: 24px; font-size: 0.9rem; color: #555; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Reply from {app_name}</h1>
            </div>
            <div class="content">
                <p>Dear {message.name},</p>
                <p>{payload.message}</p>
                <div class="original">
                    <h3>----- Original Message -----</h3>
                    <p><strong>Subject:</strong> {message.subject}</p>
                    <p><strong>From:</strong> {message.name} ({message.email})</p>
                    <p><strong>Message:</strong></p>
                    <p>{message.message}</p>
                </div>
            </div>
            <div class="footer">
                <p>This message was sent to you from {app_name} in response to your enquiry.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
Dear {message.name},

{payload.message}

----- Original Message -----
Subject: {message.subject}
From: {message.name} <{message.email}>

{message.message}

This message was sent to you from {app_name} in response to your enquiry.
""".strip()

    # Persist reply details on the message
    from datetime import datetime

    message.reply_subject = subject
    message.reply_message = payload.message
    message.replied_at = datetime.utcnow()
    message.replied_by = f"{current_user.firstname} {current_user.lastname}".strip()
    message.replied_by_role = current_user.role
    message.is_read = True

    db.commit()
    db.refresh(message)

    # Send reply email (non-blocking)
    run_async_safe(
        EmailService.send_email(
            to_email=message.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
    )

    return {
        "detail": "Reply email queued for sending",
        "id": message.id,
        "email": message.email,
        "reply_subject": message.reply_subject,
        "reply_message": message.reply_message,
        "replied_at": message.replied_at.isoformat() if message.replied_at else None,
        "replied_by": message.replied_by,
        "replied_by_role": message.replied_by_role,
    }

