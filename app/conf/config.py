from os import path
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Database Configuration
    MYSQL_PASS:str = os.getenv("MYSQL_PASS")
    MYSQL_USER:str = os.getenv("MYSQL_USER")
    MYSQL_DB_NAME:str = os.getenv("MYSQL_DB_NAME")
    MYSQL_HOST:str = os.getenv("MYSQL_HOST")

    DATABASE_URL: str = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:3306/{MYSQL_DB_NAME}" #3306

    # Database connection pool (global / shared engine)
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "30"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "60"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    # Smaller pools for per-tenant engines in multi-tenant mode
    TENANT_DB_POOL_SIZE: int = int(os.getenv("TENANT_DB_POOL_SIZE", "2"))
    TENANT_DB_MAX_OVERFLOW: int = int(os.getenv("TENANT_DB_MAX_OVERFLOW", "3"))
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # CORS Configuration
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    
    # Application
    # Default name is EduSphere, but can be overridden via APP_NAME in the .env file
    APP_NAME: str = os.getenv("APP_NAME", "EduSphere")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # When true, startup_seed truncates ALL tables (except alembic_version) then seeds a dev superadmin.
    # Default false — never wipe production data on app restart.
    STARTUP_TRUNCATE_ALL: bool = os.getenv("STARTUP_TRUNCATE_ALL", "false").lower() == "true"
    
    # Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "pjun iplg ctrq zywy")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "EduSphere")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "True").lower() == "true"
    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "False").lower() == "true"

    # Logging
    LOG_FILE: str = path.join(path.dirname(path.dirname(__file__)), "helpers", "logs", "app.log")

    # Firebase Admin (FCM server-side). Use path to service account JSON, or raw JSON for containers.
    FIREBASE_SERVICE_ACCOUNT_PATH: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
    FIREBASE_SERVICE_ACCOUNT_JSON: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    
    # Firebase Messaging (optional - for .env fallback)
    FIREBASE_MESSAGING_ENABLED: Optional[bool] = None
    FIREBASE_API_KEY: Optional[str] = None
    FIREBASE_AUTH_DOMAIN: Optional[str] = None
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_MESSAGING_SENDER_ID: Optional[str] = None
    FIREBASE_APP_ID: Optional[str] = None
    FIREBASE_VAPID_KEY: Optional[str] = None
    
    # Emails
    SYSTEM_ADMIN_NOTIFICATION_EMAILS: Optional[str] = ""
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def system_admin_notification_emails(self) -> List[str]:
        """
        Get system admin notification emails from environment.
        Returns at most 3 cleaned email strings.
        """
        if not self.SYSTEM_ADMIN_NOTIFICATION_EMAILS:
            return []
        emails = [
            email.strip()
            for email in self.SYSTEM_ADMIN_NOTIFICATION_EMAILS.split(",")
            if email.strip()
        ]
        # Limit to 3 as per requirement
        return emails[:3]

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()