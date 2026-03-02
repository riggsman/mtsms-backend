from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://root@localhost:3306/global")
    
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
    
    # Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "EduSphere")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "True").lower() == "true"
    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "False").lower() == "true"

    # System admin notification emails (fallback if not configured in DB)
    # Comma-separated list in .env, e.g. "admin1@example.com,admin2@example.com"
    SYSTEM_ADMIN_NOTIFICATION_EMAILS: str = os.getenv("SYSTEM_ADMIN_NOTIFICATION_EMAILS", "")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
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