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
    async def send_student_registration_email(
        student_name: str,
        student_email: str,
        student_id: str,
        institution_name: Optional[str] = None
    ) -> bool:
        """Send email to student after registration"""
        subject = f"Welcome to {settings.APP_NAME} - Student Registration Complete"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #9C27B0; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .info {{ background-color: #fff; padding: 15px; border-left: 4px solid #9C27B0; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to {settings.APP_NAME}!</h1>
                </div>
                <div class="content">
                    <p>Dear {student_name},</p>
                    <p>Your student account has been successfully registered{f' at {institution_name}' if institution_name else ''}.</p>
                    
                    <div class="info">
                        <h3>Your Registration Details:</h3>
                        <p><strong>Student ID:</strong> {student_id}</p>
                        <p><strong>Email:</strong> {student_email}</p>
                        <p><strong>Name:</strong> {student_name}</p>
                    </div>
                    
                    <p>Your account has been created and you can now access the student portal using your registered email address.</p>
                    
                    <p>If you have any questions or need assistance, please contact your institution's administration office.</p>
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
        
        Dear {student_name},
        
        Your student account has been successfully registered{f' at {institution_name}' if institution_name else ''}.
        
        Your Registration Details:
        Student ID: {student_id}
        Email: {student_email}
        Name: {student_name}
        
        Your account has been created and you can now access the student portal using your registered email address.
        
        If you have any questions or need assistance, please contact your institution's administration office.
        
        This is an automated message from {settings.APP_NAME}
        """
        
        return await EmailService.send_email(
            to_email=student_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    @staticmethod
    async def send_student_password_assignment_email(
        student_name: str,
        student_email: str,
        student_id: str,
        username: str,
        password: str,
        must_change_password: bool = True,
        institution_name: Optional[str] = None,
        login_url: Optional[str] = None
    ) -> bool:
        """Send email to student when password is assigned"""
        subject = f"{settings.APP_NAME} - Your Account Password Has Been Assigned"
        
        # Determine instructions based on must_change_password setting
        if must_change_password:
            password_instructions = """
                    <div class="warning">
                        <h3>⚠️ Important Security Notice:</h3>
                        <p><strong>You will be required to change this password on your first login.</strong></p>
                        <p>For your security, please log in and set a new password that only you know.</p>
                    </div>
            """
            password_text_instructions = """
IMPORTANT SECURITY NOTICE:
You will be required to change this password on your first login.
For your security, please log in and set a new password that only you know.
            """
        else:
            password_instructions = """
                    <div class="info">
                        <h3>Security Reminder:</h3>
                        <p>Please keep your password secure and do not share it with anyone.</p>
                        <p>If you suspect your account has been compromised, please contact your administrator immediately.</p>
                    </div>
            """
            password_text_instructions = """
SECURITY REMINDER:
Please keep your password secure and do not share it with anyone.
If you suspect your account has been compromised, please contact your administrator immediately.
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #9C27B0; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .credentials {{ background-color: #fff; padding: 15px; border-left: 4px solid #9C27B0; margin: 20px 0; }}
                .warning {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #FF9800; margin: 20px 0; }}
                .info {{ background-color: #e3f2fd; padding: 15px; border-left: 4px solid #2196F3; margin: 20px 0; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #9C27B0; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Your Account Password Has Been Assigned</h1>
                </div>
                <div class="content">
                    <p>Dear {student_name},</p>
                    <p>Your account password has been assigned{f' for {institution_name}' if institution_name else ''}.</p>
                    
                    <div class="credentials">
                        <h3>Your Login Credentials:</h3>
                        <p><strong>Student ID:</strong> {student_id}</p>
                        <p><strong>Username:</strong> {username}</p>
                        <p><strong>Email:</strong> {student_email}</p>
                        <p><strong>Password:</strong> <code style="background-color: #f5f5f5; padding: 4px 8px; border-radius: 3px; font-family: monospace;">{password}</code></p>
                    </div>
                    
                    {password_instructions}
                    
                    {f'<p><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></p>' if login_url else ''}
                    
                    {f'<a href="{login_url}" class="button">Login to Your Account</a>' if login_url else ''}
                    
                    <p>If you have any questions or need assistance, please contact your institution's administration office.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from {settings.APP_NAME}</p>
                    <p><strong>Please keep this email secure and do not share your password with anyone.</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Your Account Password Has Been Assigned
        
        Dear {student_name},
        
        Your account password has been assigned{f' for {institution_name}' if institution_name else ''}.
        
        Your Login Credentials:
        Student ID: {student_id}
        Username: {username}
        Email: {student_email}
        Password: {password}
        
        {password_text_instructions}
        
        {f'Login URL: {login_url}' if login_url else ''}
        
        If you have any questions or need assistance, please contact your institution's administration office.
        
        This is an automated message from {settings.APP_NAME}
        
        Please keep this email secure and do not share your password with anyone.
        """
        
        return await EmailService.send_email(
            to_email=student_email,
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
    
    @staticmethod
    async def send_student_suspension_email(
        student_name: str,
        student_email: str,
        student_id: str,
        reason: str,
        institution_name: Optional[str] = None,
        login_url: Optional[str] = None
    ) -> bool:
        """Send email to student informing them of their account suspension"""
        subject = f"{settings.APP_NAME} - Account Suspension Notice"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .warning {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #dc3545; margin: 20px 0; }}
                .reason-box {{ background-color: #fff; padding: 15px; border-left: 4px solid #dc3545; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Account Suspension Notice</h1>
                </div>
                <div class="content">
                    <p>Dear {student_name},</p>
                    <p>We regret to inform you that your account{f' at {institution_name}' if institution_name else ''} has been suspended.</p>
                    
                    <div class="warning">
                        <h3>⚠️ Important Notice</h3>
                        <p>Your account access has been temporarily restricted. You will not be able to log in until further notice.</p>
                    </div>
                    
                    <div class="reason-box">
                        <h3>Reason for Suspension:</h3>
                        <p><strong>{reason}</strong></p>
                    </div>
                    
                    <p>If you believe this suspension is in error or have questions about this action, please contact your institution's administration office immediately.</p>
                    
                    {f'<p>You can reach out to us at: <a href="{login_url}">{login_url}</a></p>' if login_url else ''}
                    
                    <p>We encourage you to address any concerns promptly to resolve this matter.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from {settings.APP_NAME}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Account Suspension Notice
        
        Dear {student_name},
        
        We regret to inform you that your account{f' at {institution_name}' if institution_name else ''} has been suspended.
        
        Important Notice:
        Your account access has been temporarily restricted. You will not be able to log in until further notice.
        
        Reason for Suspension:
        {reason}
        
        If you believe this suspension is in error or have questions about this action, please contact your institution's administration office immediately.
        
        {f'You can reach out to us at: {login_url}' if login_url else ''}
        
        We encourage you to address any concerns promptly to resolve this matter.
        
        This is an automated message from {settings.APP_NAME}
        """
        
        return await EmailService.send_email(
            to_email=student_email,
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
