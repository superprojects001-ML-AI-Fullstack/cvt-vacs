"""
Configuration settings for CVT-VACS Backend
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "CVT-VACS API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # MongoDB
    MONGODB_URL: str
    DATABASE_NAME: str = "cvt_vacs_db"
    
    # JWT Token Settings
    SECRET_KEY: str
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


@lru_cache()
def get_settings() -> Settings:
    return Settings()
