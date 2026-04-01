"""
Configuration settings for CVT-VACS Backend
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "CVT-VACS API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # MongoDB - Add defaults for Render deployment
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "cvt_vacs_db")
    
    # JWT Token Settings - Add default for testing
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    TOKEN_EXPIRY_HOURS: int = 24
    
    # Twilio SMS (Optional)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    
    # ANPR Settings
    YOLO_MODEL_PATH: str = "yolov8n.pt"
    CONFIDENCE_THRESHOLD: float = 0.5
    PLATE_CONFIDENCE_THRESHOLD: float = 0.7
    
    # System Settings
    MAX_FAILED_ATTEMPTS: int = 3
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra env vars


@lru_cache()
def get_settings() -> Settings:
    return Settings()