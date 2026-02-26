# Email Configuration Guide

## Overview
The email service has been successfully integrated into the application. Emails are sent asynchronously (non-blocking) for:
- Tenant registration
- Lecturer/Staff registration
- Password change notifications

## Configuration

### Step 1: Update .env File
The email configuration has been added to your `.env` file. You need to fill in your SMTP credentials:

```env
# Email Configuration
EMAIL_ENABLED=True
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=School Management System
SMTP_USE_TLS=True
```

### Step 2: Gmail Setup (if using Gmail)

1. **Enable 2-Factor Authentication** on your Google account
2. **Generate an App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a new app password for "Mail"
   - Use this app password (not your regular password) in `SMTP_PASSWORD`

### Step 3: Other Email Providers

#### Outlook/Hotmail:
```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=True
```

#### Yahoo:
```env
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USE_TLS=True
```

#### Custom SMTP Server:
```env
SMTP_HOST=your-smtp-server.com
SMTP_PORT=587  # or 465 for SSL
SMTP_USE_TLS=True  # or False for SSL
```

## Testing

### Enable/Disable Email
Set `EMAIL_ENABLED=False` to disable email sending (useful for development/testing).

When disabled, emails are logged but not sent.

## Email Templates

### 1. Tenant Registration Email
- Sent to tenant admin after registration
- Includes: tenant name, username, password, login URL
- HTML and plain text versions

### 2. Lecturer/Staff Registration Email
- Sent to lecturer after account creation
- Includes: employee ID, username, password
- HTML and plain text versions

### 3. Password Change Notification
- Sent when password is changed
- Includes security notice
- Distinguishes between self-change and admin-initiated change

## Troubleshooting

### Emails Not Sending
1. Check `EMAIL_ENABLED=True` in .env
2. Verify SMTP credentials are correct
3. Check server logs for error messages
4. Ensure firewall allows SMTP connections (port 587 or 465)

### Gmail Issues
- Use App Password, not regular password
- Ensure "Less secure app access" is enabled (if not using App Password)
- Check if account has 2FA enabled

### Common Errors
- **Authentication failed**: Check SMTP_USER and SMTP_PASSWORD
- **Connection timeout**: Check SMTP_HOST and SMTP_PORT
- **TLS error**: Try setting SMTP_USE_TLS=False for SSL connections

## Dependencies

The following package has been installed:
- `aiosmtplib` - Async SMTP library for sending emails

## Notes

- All email sending is **asynchronous** and **non-blocking**
- Email failures won't break the registration/password change process
- Email errors are logged for debugging
- Emails include both HTML and plain text versions for compatibility
