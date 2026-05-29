-- Email Tracking System Database Migration
-- Run this SQL script to create the email_logs table

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

-- Add comments for documentation
ALTER TABLE email_logs 
    MODIFY COLUMN status VARCHAR(20) NOT NULL DEFAULT 'PENDING' 
    COMMENT 'Status: PENDING, SENT, FAILED, DELIVERED, BOUNCED';
