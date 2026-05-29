-- Migration: add firebase storage_bucket and measurement_id columns
-- Run this SQL to add missing columns to system_settings table

ALTER TABLE system_settings 
ADD COLUMN firebase_storage_bucket VARCHAR(255) NULL,
ADD COLUMN firebase_measurement_id VARCHAR(255) NULL;

-- Update existing record with correct Firebase config
UPDATE system_settings 
SET 
    firebase_api_key = 'AIzaSyC5ju7WE_Uc5KXM0wqMUtwmfhHIo4ZPPyA',
    firebase_auth_domain = 'wireit-91b12.firebaseapp.com',
    firebase_project_id = 'wireit-91b12',
    firebase_storage_bucket = 'wireit-91b12.appspot.com',
    firebase_messaging_sender_id = '204834509466',
    firebase_app_id = '1:204834509466:web:722803d25b5a21f8ff4523',
    firebase_measurement_id = 'G-HK25N9X6SG',
    firebase_messaging_enabled = 1
WHERE id = 1;