# Email Tracking System Setup Guide

## Overview
The email tracking system has been implemented with retry logic and webhook support. All emails sent through the application are now tracked with status updates.

## Database Setup

### Step 1: Run the Migration Script
Execute the SQL migration script to create the `email_logs` table:

```bash
mysql -u your_username -p your_database < EMAIL_TRACKING_MIGRATION.sql
```

Or manually run the SQL in your MySQL client:
```sql
CREATE TABLE IF NOT EXISTS email_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sender_email VARCHAR(255) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    failure_reason TEXT NULL,
    provider_message_id VARCHAR(255) NULL,
    retry_count INT DEFAULT 0 NOT NULL,
    institution_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NULL,
    INDEX idx_provider_message_id (provider_message_id),
    INDEX idx_institution_id (institution_id),
    INDEX idx_status (status),
    INDEX idx_recipient_email (recipient_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## Email Status Flow

```
PENDING → SENT → DELIVERED (or BOUNCED)
         ↓
      FAILED (if retries exhausted)
```

### Status Values:
- **PENDING**: Email log created, sending in progress
- **SENT**: Email successfully sent to SMTP server
- **FAILED**: Failed after max retries (3 attempts)
- **DELIVERED**: Confirmed delivered via webhook
- **BOUNCED**: Email bounced via webhook

## Features Implemented

### 1. Automatic Email Tracking
All emails sent through the application are automatically tracked:
- User registration emails (students and staff)
- Password assignment emails
- Account suspension emails

### 2. Retry Logic
- Maximum 3 retry attempts for failed emails
- Automatic retry on failure
- Failure reason logged

### 3. Webhook Support
Webhook endpoint available at:
```
POST /api/v1/email-logs/webhook/delivery-status
```

### 4. Email Statistics Dashboard
View email statistics in the overview dashboard:
- Total emails sent
- Pending, Sent, Failed, Delivered, Bounced counts
- Success rate calculation

## API Endpoints

### Get Email Logs
```
GET /api/v1/email-logs?page=1&page_size=50&status=SENT&recipient_email=user@example.com
```

### Get Email Statistics
```
GET /api/v1/email-logs/stats
```

### Get Specific Email Log
```
GET /api/v1/email-logs/{log_id}
```

### Webhook Endpoint (for email providers)
```
POST /api/v1/email-logs/webhook/delivery-status
Body: {
    "message_id": "provider_message_id",
    "event": "delivered" | "bounced" | "failed"
}
```

## Webhook Configuration

### For SendGrid:
1. Go to SendGrid Dashboard → Settings → Mail Settings → Event Webhook
2. Add webhook URL: `https://your-domain.com/api/v1/email-logs/webhook/delivery-status`
3. Select events: `delivered`, `bounced`, `failed`
4. Save configuration

### For Mailgun:
1. Go to Mailgun Dashboard → Sending → Webhooks
2. Add webhook URL: `https://your-domain.com/api/v1/email-logs/webhook/delivery-status`
3. Select events: `delivered`, `bounced`, `failed`
4. Save configuration

### For Other Providers:
Configure webhook to POST to the endpoint with:
- `message_id` or `provider_message_id`: The message ID from the provider
- `event` or `event_type`: One of: `delivered`, `bounced`, `failed`

## Testing

### Test Email Tracking
1. Create a new user (student or staff)
2. Check the email logs: `GET /api/v1/email-logs`
3. Verify the email log entry is created with status `PENDING` or `SENT`

### Test Webhook
1. Send a test webhook request:
```bash
curl -X POST https://your-domain.com/api/v1/email-logs/webhook/delivery-status \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "test_msg_123",
    "event": "delivered"
  }'
```

2. Verify the email log status is updated

## Monitoring

### View Email Statistics
- Navigate to the Overview dashboard
- Check the "Email Tracking" card for real-time statistics

### Check Failed Emails
- Filter email logs by status: `GET /api/v1/email-logs?status=FAILED`
- Review `failure_reason` field for details

## Troubleshooting

### Emails Not Being Tracked
1. Verify the `email_logs` table exists
2. Check application logs for errors
3. Ensure EmailTracker is being used (not direct EmailService calls)

### Webhook Not Updating Status
1. Verify webhook URL is accessible
2. Check webhook payload format matches expected structure
3. Review application logs for webhook errors

### High Failure Rate
1. Check SMTP configuration
2. Review `failure_reason` in email logs
3. Verify email provider credentials

## Notes

- Email tracking is automatic for all emails sent through EmailTracker
- Retry logic attempts up to 3 times before marking as FAILED
- Webhook updates are asynchronous and don't block email sending
- Email statistics are filtered by institution_id for tenant admins
- System admins can view all email logs across all institutions
