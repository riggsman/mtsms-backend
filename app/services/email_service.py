import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
import asyncio
from app.conf.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Async email service for sending emails"""
    
    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> bool:
        """
        Send an email asynchronously
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content (optional)
            from_email: Sender email (defaults to SMTP_FROM_EMAIL)
            from_name: Sender name (defaults to SMTP_FROM_NAME)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        # Check if email is enabled
        if not settings.EMAIL_ENABLED:
            logger.info(f"Email sending is disabled. Would send to {to_email}: {subject}")
            return False
        
        # Validate email configuration
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured. Email not sent.")
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{from_name or settings.SMTP_FROM_NAME} <{from_email or settings.SMTP_FROM_EMAIL}>"
            message["To"] = to_email
            
            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)
            
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email asynchronously
            # Handle different SMTP configurations:
            # - Port 587: Uses STARTTLS (TLS upgrade after connection) - use start_tls=True
            # - Port 465: Uses SSL/TLS from the start (implicit SSL) - use SSL context
            
            if settings.SMTP_PORT == 465:
                # Port 465 uses implicit SSL/TLS
                import ssl
                ssl_context = ssl.create_default_context()
                async with aiosmtplib.SMTP(
                    hostname=settings.SMTP_HOST,
                    port=settings.SMTP_PORT,
                    use_tls=True,  # Use TLS for port 465
                    tls_context=ssl_context,
                ) as smtp:
                    await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    await smtp.send_message(message)
            else:
                # Port 587 or other ports use STARTTLS
                # Use SMTP class for better control over STARTTLS
                async with aiosmtplib.SMTP(
                    hostname=settings.SMTP_HOST,
                    port=settings.SMTP_PORT,
                    use_tls=False,  # Don't use implicit TLS
                    start_tls=settings.SMTP_USE_TLS,  # Enable STARTTLS
                ) as smtp:
                    await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    await smtp.send_message(message)
            
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    async def send_tenant_registration_email(
        tenant_name: str,
        admin_email: str,
        admin_username: str,
        admin_password: str,
        domain: Optional[str] = None
    ) -> bool:
        """Send email to tenant admin after registration"""
        subject = f"Welcome to {settings.APP_NAME} - Tenant Registration Complete"
        
        login_url = f"https://{domain}" if domain else "https://your-domain.com"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .credentials {{ background-color: #fff; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to {settings.APP_NAME}!</h1>
                </div>
                <div class="content">
                    <p>Dear Administrator,</p>
                    <p>Your tenant account <strong>{tenant_name}</strong> has been successfully registered.</p>
                    
                    <div class="credentials">
                        <h3>Your Login Credentials:</h3>
                        <p><strong>Username:</strong> {admin_username}</p>
                        <p><strong>Password:</strong> {admin_password}</p>
                        <p><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></p>
                    </div>
                    
                    <p><strong>Important:</strong> Please change your password after your first login for security purposes.</p>
                    
                    <a href="{login_url}" class="button">Login to Your Account</a>
                    
                    <p>If you have any questions, please contact our support team.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from {settings.APP_NAME}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to {settings.APP_NAME}!
        
        Your tenant account {tenant_name} has been successfully registered.
        
        Your Login Credentials:
        Username: {admin_username}
        Password: {admin_password}
        Login URL: {login_url}
        
        Important: Please change your password after your first login for security purposes.
        
        If you have any questions, please contact our support team.
        
        This is an automated message from {settings.APP_NAME}
        """
        
        return await EmailService.send_email(
            to_email=admin_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    @staticmethod
    async def send_lecturer_registration_email(
        lecturer_name: str,
        lecturer_email: str,
        username: str,
        password: str,
        employee_id: str,
        institution_name: Optional[str] = None
    ) -> bool:
        """Send email to staff after registration"""
        subject = f"Welcome to {settings.APP_NAME} - Staff Account Created"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .credentials {{ background-color: #fff; padding: 15px; border-left: 4px solid #2196F3; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to {settings.APP_NAME}!</h1>
                </div>
                <div class="content">
                    <p>Dear {lecturer_name},</p>
                    <p>Your staff account has been successfully created{f' for {institution_name}' if institution_name else ''}.</p>
                    
                    <div class="credentials">
                        <h3>Your Login Credentials:</h3>
                        <p><strong>Employee ID:</strong> {employee_id}</p>
                        <p><strong>Username:</strong> {username}</p>
                        <p><strong>Password:</strong> {password}</p>
                        <p><strong>Email:</strong> {lecturer_email}</p>
                    </div>
                    
                    <p><strong>Important:</strong> You will be required to change your password on your first login for security purposes.</p>
                    
                    <p>If you have any questions, please contact your administrator.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from {settings.APP_NAME}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to {settings.APP_NAME}!
        
        Dear {lecturer_name},
        
        Your staff account has been successfully created{f' for {institution_name}' if institution_name else ''}.
        
        Your Login Credentials:
        Employee ID: {employee_id}
        Username: {username}
        Password: {password}
        Email: {lecturer_email}
        
        Important: You will be required to change your password on your first login for security purposes.
        
        If you have any questions, please contact your administrator.
        
        This is an automated message from {settings.APP_NAME}
        """
        
        return await EmailService.send_email(
            to_email=lecturer_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    @staticmethod
    async def send_password_change_email(
        user_name: str,
        user_email: str,
        changed_by_admin: bool = False,
        admin_name: Optional[str] = None
    ) -> bool:
        """Send email notification when password is changed"""
        subject = f"{settings.APP_NAME} - Password Changed Successfully"
        
        change_info = f"by administrator {admin_name}" if changed_by_admin and admin_name else "by you"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #FF9800; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .warning {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #FF9800; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Changed Successfully</h1>
                </div>
                <div class="content">
                    <p>Dear {user_name},</p>
                    <p>This is to confirm that your password has been changed {change_info}.</p>
                    
                    <div class="warning">
                        <h3>Security Notice:</h3>
                        <p>If you did not make this change, please contact your administrator immediately and secure your account.</p>
                    </div>
                    
                    <p>If you have any questions or concerns, please contact our support team.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from {settings.APP_NAME}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Changed Successfully
        
        Dear {user_name},
        
        This is to confirm that your password has been changed {change_info}.
        
        Security Notice:
        If you did not make this change, please contact your administrator immediately and secure your account.
        
        If you have any questions or concerns, please contact our support team.
        
        This is an automated message from {settings.APP_NAME}
        """
        
        return await EmailService.send_email(
            to_email=user_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )


# Background task helper (deprecated - use run_async_safe from async_helper instead)
def send_email_background(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
):
    """Helper function to send email in background task"""
    from app.helpers.async_helper import run_async_safe
    run_async_safe(
        EmailService.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    )
