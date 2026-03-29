"""
Pydantic Models for Data Validation
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AccessDecision(str, Enum):
    GRANTED = "GRANTED"
    DENIED = "DENIED"
    PENDING = "PENDING"


class VehicleType(str, Enum):
    SEDAN = "sedan"
    SUV = "suv"
    TRUCK = "truck"
    VAN = "van"
    MOTORCYCLE = "motorcycle"
    OTHER = "other"


class TokenType(str, Enum):
    JWT = "jwt"
    QR = "qr"
    OTP = "otp"


# ============== User Models ==============
class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    user_id: str
    created_at: datetime
    is_active: bool = True
    
    class Config:
        from_attributes = True


# ============== Vehicle Models ==============
class VehicleBase(BaseModel):
    plate_number: str = Field(..., min_length=3, max_length=20)
    vehicle_type: VehicleType = VehicleType.SEDAN
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None


class VehicleCreate(VehicleBase):
    user_id: str


class VehicleResponse(VehicleBase):
    id: str
    user_id: str
    registered_at: datetime
    status: str = "active"
    last_access: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============== Token Models ==============
class TokenBase(BaseModel):
    plate_number: str
    token_type: TokenType = TokenType.JWT


class TokenCreate(TokenBase):
    user_id: str
    expiry_hours: Optional[int] = 24


class TokenResponse(BaseModel):
    token_id: str
    token_string: str
    plate_number: str
    expiry_time: datetime
    created_at: datetime
    is_revoked: bool = False
    
    class Config:
        from_attributes = True


class TokenVerifyRequest(BaseModel):
    token: str
    plate_number: str


class TokenVerifyResponse(BaseModel):
    valid: bool
    token_id: Optional[str] = None
    plate_number: Optional[str] = None
    message: str


# ============== ANPR Models ==============
class ANPRRequest(BaseModel):
    image_base64: Optional[str] = None
    use_camera: bool = False


class ANPRResult(BaseModel):
    success: bool
    plate_number: Optional[str] = None
    confidence: Optional[float] = None
    vehicle_type: Optional[str] = None
    bounding_box: Optional[Dict[str, int]] = None
    processing_time_ms: Optional[float] = None
    message: Optional[str] = None


# ============== Access Control Models ==============
class AccessRequest(BaseModel):
    token: str
    plate_number: Optional[str] = None  # If not provided, ANPR will be used
    image_base64: Optional[str] = None  # For ANPR


class AccessResponse(BaseModel):
    decision: AccessDecision
    token_valid: bool
    plate_recognized: bool
    plate_match: bool
    recognized_plate: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: datetime
    message: str
    log_id: Optional[str] = None


# ============== Access Log Models ==============
class AccessLogBase(BaseModel):
    plate_number: str
    token_id: str
    access_decision: AccessDecision
    token_valid: bool
    plate_recognized: bool
    plate_match: bool
    confidence: Optional[float] = None
    anpr_processing_time_ms: Optional[float] = None
    token_verification_time_ms: Optional[float] = None
    total_response_time_ms: Optional[float] = None


class AccessLogResponse(AccessLogBase):
    id: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


# ============== Statistics Models ==============
class SystemStatistics(BaseModel):
    total_users: int
    total_vehicles: int
    total_tokens_issued: int
    total_access_logs: int
    today_attempts: int
    today_granted: int
    today_denied: int


class PerformanceMetrics(BaseModel):
    anpr_accuracy: float
    anpr_precision: float
    anpr_recall: float
    anpr_f1_score: float
    token_verification_latency_ms: float
    system_response_time_ms: float
    authentication_success_rate: float
    throughput_vehicles_per_minute: float
    false_positive_rate: float
    false_negative_rate: float
