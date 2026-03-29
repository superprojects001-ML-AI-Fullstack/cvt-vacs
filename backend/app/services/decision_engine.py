"""
Decision Engine: Two-Factor Authentication for Vehicle Access Control
Implements: Access = A · T · M (ANPR validity · Token validity · Plate Match)
"""
from datetime import datetime
from typing import Dict, Any, Optional

from app.services.token_service import TokenService
from app.services.anpr_service import ANPRService
from app.database import db
from app.models.schemas import AccessDecision


class DecisionEngine:
    """
    Decision Engine implementing 2FA logic
    
    Mathematical Model:
    - A = ANPR output validity (1 if confidence >= threshold, 0 otherwise)
    - T = Token validity (1 if valid and not expired, 0 otherwise)
    - M = Plate matching condition (1 if detected == registered, 0 otherwise)
    - Access = A · T · M (All must be 1 for access to be granted)
    """
    
    @staticmethod
    async def evaluate_access(
        token: str,
        image_base64: Optional[str] = None,
        detected_plate: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate access request using 2FA
        
        Args:
            token: Authentication token (JWT/QR/OTP)
            image_base64: Vehicle image for ANPR (optional if plate provided)
            detected_plate: Pre-detected plate number (optional)
            
        Returns:
            Access decision with full evaluation details
        """
        total_start = datetime.utcnow()
        
        # ========== STEP 1: ANPR Processing (A) ==========
        anpr_result = None
        anpr_valid = False
        
        if detected_plate is None and image_base64:
            # Run ANPR on provided image
            anpr_result = await ANPRService.process_image(image_base64)
            anpr_valid = anpr_result.get("success", False)
            detected_plate = anpr_result.get("plate_number") if anpr_valid else None
        elif detected_plate:
            # Plate provided directly (e.g., from manual entry)
            anpr_valid = True
            anpr_result = {
                "success": True,
                "plate_number": detected_plate,
                "confidence": 1.0,
                "processing_time_ms": 0
            }
        else:
            # No image and no plate - cannot proceed
            return {
                "decision": AccessDecision.DENIED,
                "token_valid": False,
                "plate_recognized": False,
                "plate_match": False,
                "recognized_plate": None,
                "confidence": None,
                "timestamp": datetime.utcnow(),
                "message": "No image or plate number provided for verification",
                "log_id": None
            }
        
        anpr_time = anpr_result.get("processing_time_ms", 0) if anpr_result else 0
        
        # ========== STEP 2: Token Verification (T) ==========
        token_start = datetime.utcnow()
        token_result = await TokenService.verify_token_for_access(token, detected_plate or "")
        token_time = (datetime.utcnow() - token_start).total_seconds() * 1000
        
        token_valid = token_result.get("token_valid", False)
        plate_match = token_result.get("plate_match", False)
        registered_plate = token_result.get("registered_plate")
        
        # ========== STEP 3: Decision Fusion (Access = A · T · M) ==========
        # All three conditions must be true
        access_granted = anpr_valid and token_valid and plate_match
        
        if access_granted:
            decision = AccessDecision.GRANTED
            message = "Access granted - 2FA verification successful"
        else:
            decision = AccessDecision.DENIED
            
            # Determine specific reason
            if not anpr_valid:
                message = "Access denied - License plate not recognized"
            elif not token_valid:
                message = "Access denied - Invalid or expired token"
            elif not plate_match:
                message = f"Access denied - Plate mismatch (Registered: {registered_plate}, Detected: {detected_plate})"
            else:
                message = "Access denied - Unknown error"
        
        total_time = (datetime.utcnow() - total_start).total_seconds() * 1000
        
        # ========== STEP 4: Log Access Attempt ==========
        log_data = {
            "plate_number": detected_plate or "UNKNOWN",
            "token_id": token_result.get("token_id", "UNKNOWN"),
            "access_decision": decision,
            "token_valid": token_valid,
            "plate_recognized": anpr_valid,
            "plate_match": plate_match,
            "confidence": anpr_result.get("confidence") if anpr_result else None,
            "anpr_processing_time_ms": anpr_time,
            "token_verification_time_ms": token_time,
            "total_response_time_ms": total_time,
            "timestamp": datetime.utcnow()
        }
        
        try:
            log_id = await db.log_access_attempt(log_data)
        except Exception as e:
            print(f"Failed to log access: {e}")
            log_id = None
        
        # ========== STEP 5: Return Result ==========
        return {
            "decision": decision,
            "token_valid": token_valid,
            "plate_recognized": anpr_valid,
            "plate_match": plate_match,
            "recognized_plate": detected_plate,
            "registered_plate": registered_plate,
            "confidence": anpr_result.get("confidence") if anpr_result else None,
            "timestamp": datetime.utcnow(),
            "message": message,
            "log_id": log_id,
            "processing_times": {
                "anpr_ms": anpr_time,
                "token_verification_ms": token_time,
                "total_ms": total_time
            }
        }
    
    @staticmethod
    async def evaluate_manual_access(
        token: str,
        manual_plate: str
    ) -> Dict[str, Any]:
        """
        Evaluate access with manually entered plate (for testing/backup)
        
        Args:
            token: Authentication token
            manual_plate: Manually entered plate number
            
        Returns:
            Access decision
        """
        return await DecisionEngine.evaluate_access(
            token=token,
            detected_plate=manual_plate
        )
    
    @staticmethod
    def calculate_decision_confidence(
        anpr_confidence: float,
        token_valid: bool,
        plate_match: bool
    ) -> float:
        """
        Calculate overall confidence score for the decision
        
        Formula: confidence = anpr_confidence * (1 if token_valid else 0) * (1 if plate_match else 0)
        
        Args:
            anpr_confidence: Confidence from ANPR (0-1)
            token_valid: Whether token is valid
            plate_match: Whether plates match
            
        Returns:
            Overall confidence score (0-1)
        """
        token_score = 1.0 if token_valid else 0.0
        match_score = 1.0 if plate_match else 0.0
        
        return anpr_confidence * token_score * match_score
