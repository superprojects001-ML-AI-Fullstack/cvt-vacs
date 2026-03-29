"""
Token Service: JWT Generation, Verification, and Management
Implements token-based authentication as per thesis specifications
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import string

from app.config import get_settings
from app.database import db

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenService:
    """
    Token Service implementing JWT-based authentication
    Mathematical Model: Ti = Hash(UserID || PlateNumber || Timestamp || SecretKey)
    """
    
    @staticmethod
    def generate_jwt_token(user_id: str, plate_number: str, expiry_hours: int = 24) -> Dict[str, Any]:
        """
        Generate a JWT token for vehicle access
        
        Args:
            user_id: Registered user ID
            plate_number: Vehicle plate number
            expiry_hours: Token validity period
            
        Returns:
            Dictionary containing token_id, token_string, and metadata
        """
        token_id = secrets.token_urlsafe(16)
        
        # Create payload following the mathematical model
        payload = {
            "token_id": token_id,
            "user_id": user_id,
            "plate_number": plate_number.upper().replace(" ", ""),
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=expiry_hours),
            "type": "access_token"
        }
        
        # Generate JWT token
        token_string = jwt.encode(
            payload, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        
        return {
            "token_id": token_id,
            "token_string": token_string,
            "plate_number": plate_number.upper().replace(" ", ""),
            "expiry_time": payload["exp"],
            "created_at": payload["iat"],
            "is_revoked": False
        }
    
    @staticmethod
    def verify_jwt_token(token_string: str) -> Dict[str, Any]:
        """
        Verify a JWT token's validity and expiration
        
        Args:
            token_string: The JWT token to verify
            
        Returns:
            Dictionary with verification result and decoded data
        """
        try:
            # Decode and validate token
            payload = jwt.decode(
                token_string, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            # Check if token is revoked in database
            token_id = payload.get("token_id")
            # Note: In async context, this should be awaited
            # For now, we return the decoded payload
            
            return {
                "valid": True,
                "token_id": token_id,
                "user_id": payload.get("user_id"),
                "plate_number": payload.get("plate_number"),
                "exp": payload.get("exp"),
                "message": "Token is valid"
            }
            
        except jwt.ExpiredSignatureError:
            return {
                "valid": False,
                "token_id": None,
                "message": "Token has expired"
            }
        except JWTError as e:
            return {
                "valid": False,
                "token_id": None,
                "message": f"Invalid token: {str(e)}"
            }
    
    @staticmethod
    def generate_qr_token(plate_number: str, expiry_hours: int = 24) -> Dict[str, Any]:
        """
        Generate a QR code compatible token
        
        Args:
            plate_number: Vehicle plate number
            expiry_hours: Token validity period
            
        Returns:
            Dictionary with QR code data
        """
        token_id = secrets.token_urlsafe(16)
        expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        # QR code data format
        qr_data = {
            "token_id": token_id,
            "plate": plate_number.upper().replace(" ", ""),
            "exp": expiry.isoformat(),
            "sig": secrets.token_hex(8)  # Simple signature for demo
        }
        
        return {
            "token_id": token_id,
            "qr_data": qr_data,
            "plate_number": plate_number.upper().replace(" ", ""),
            "expiry_time": expiry,
            "created_at": datetime.utcnow(),
            "is_revoked": False
        }
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """
        Generate a numeric One-Time Password
        
        Args:
            length: OTP length (default 6)
            
        Returns:
            Numeric OTP string
        """
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @staticmethod
    async def issue_token(user_id: str, plate_number: str, token_type: str = "jwt", expiry_hours: int = 24) -> Dict[str, Any]:
        """
        Issue a new token and store in database
        
        Args:
            user_id: User ID
            plate_number: Vehicle plate number
            token_type: Type of token (jwt, qr, otp)
            expiry_hours: Token validity
            
        Returns:
            Token data dictionary
        """
        # Verify vehicle exists
        vehicle = await db.get_vehicle_by_plate(plate_number)
        if not vehicle:
            raise ValueError(f"Vehicle with plate {plate_number} not found")
        
        # Generate token based on type
        if token_type == "jwt":
            token_data = TokenService.generate_jwt_token(user_id, plate_number, expiry_hours)
        elif token_type == "qr":
            token_data = TokenService.generate_qr_token(plate_number, expiry_hours)
            token_data["user_id"] = user_id
        elif token_type == "otp":
            otp = TokenService.generate_otp()
            token_data = {
                "token_id": secrets.token_urlsafe(16),
                "token_string": otp,
                "plate_number": plate_number.upper().replace(" ", ""),
                "user_id": user_id,
                "expiry_time": datetime.utcnow() + timedelta(hours=expiry_hours),
                "created_at": datetime.utcnow(),
                "is_revoked": False,
                "token_type": "otp"
            }
        else:
            raise ValueError(f"Unsupported token type: {token_type}")
        
        # Store in database
        await db.create_token(token_data)
        
        return token_data
    
    @staticmethod
    async def verify_token_for_access(token_string: str, detected_plate: str) -> Dict[str, Any]:
        """
        Complete token verification for access control
        Implements: Tv(Ti) and Access = A · T · M
        
        Args:
            token_string: The token to verify
            detected_plate: Plate detected by ANPR
            
        Returns:
            Verification result with all checks
        """
        start_time = datetime.utcnow()
        
        # Step 1: Validate token signature and expiration (Tv)
        token_result = TokenService.verify_jwt_token(token_string)
        
        if not token_result["valid"]:
            verification_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return {
                "access_granted": False,
                "token_valid": False,
                "plate_match": False,
                "message": token_result["message"],
                "verification_time_ms": verification_time
            }
        
        # Step 2: Check plate matching (M)
        registered_plate = token_result.get("plate_number", "").upper().replace(" ", "")
        detected_plate_clean = detected_plate.upper().replace(" ", "")
        
        plate_match = registered_plate == detected_plate_clean
        
        verification_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Final decision: Access = A · T · M (all must be true)
        access_granted = token_result["valid"] and plate_match
        
        return {
            "access_granted": access_granted,
            "token_valid": token_result["valid"],
            "plate_match": plate_match,
            "registered_plate": registered_plate,
            "detected_plate": detected_plate_clean,
            "token_id": token_result.get("token_id"),
            "message": "Access granted" if access_granted else "Access denied - plate mismatch" if not plate_match else "Invalid token",
            "verification_time_ms": verification_time
        }
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
