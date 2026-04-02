"""
Access Control API Routes - Production-Ready 2FA Entry Point
Handles token + ANPR verification for vehicle access.
"""
import logging
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel, Field
from datetime import datetime

from app.services.decision_engine import DecisionEngine
from app.services.anpr_service import get_yolo_model, get_ocr_reader

# ── Router & Logger ────────────────────────────────────────────────
router = APIRouter(tags=["Access Control"])
logger = logging.getLogger("access_router")


# ── Pydantic Response Models ───────────────────────────────────────
class AccessVerificationResponse(BaseModel):
    success: bool
    decision: str
    token_valid: bool
    plate_recognized: Optional[bool] = None
    plate_match: Optional[bool] = None
    recognized_plate: Optional[str] = None
    registered_plate: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: datetime
    message: str
    log_id: Optional[str] = None
    processing_times: Optional[Dict[str, float]] = Field(default_factory=dict)


class ManualAccessResponse(BaseModel):
    success: bool
    decision: str
    token_valid: bool
    plate_match: Optional[bool] = None
    recognized_plate: Optional[str] = None
    registered_plate: Optional[str] = None
    timestamp: datetime
    message: str
    log_id: Optional[str] = None


class AccessSystemStatusResponse(BaseModel):
    status: str
    two_factor_enabled: bool
    components: Dict[str, str]
    message: str


# ── Endpoints ─────────────────────────────────────────────────────
@router.post("/verify", response_model=AccessVerificationResponse)
async def verify_access(
    token: str = Body(..., description="JWT or token for vehicle access"),
    image_base64: Optional[str] = Body(None, description="Base64-encoded image of vehicle"),
    plate_number: Optional[str] = Body(None, description="Optional manual plate number")
):
    """
    Two-Factor Authentication for vehicle access.
    Either `image_base64` or `plate_number` must be provided.
    """
    if not image_base64 and not plate_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'image_base64' or 'plate_number' must be provided"
        )

    if plate_number:
        plate_number = plate_number.upper().replace(" ", "")

    try:
        result = await DecisionEngine.evaluate_access(
            token=token,
            image_base64=image_base64,
            detected_plate=plate_number
        )

        return AccessVerificationResponse(
            success=result["decision"] == "GRANTED",
            decision=result["decision"],
            token_valid=result["token_valid"],
            plate_recognized=result.get("plate_recognized"),
            plate_match=result.get("plate_match"),
            recognized_plate=result.get("recognized_plate"),
            registered_plate=result.get("registered_plate"),
            confidence=result.get("confidence"),
            timestamp=result.get("timestamp", datetime.utcnow()),
            message=result.get("message", ""),
            log_id=result.get("log_id"),
            processing_times=result.get("processing_times", {})
        )

    except Exception as e:
        logger.error("Access verification failed", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Access verification failed due to internal error"
        )


@router.post("/verify-manual", response_model=ManualAccessResponse)
async def verify_access_manual(
    token: str = Body(..., description="JWT or token for vehicle access"),
    plate_number: str = Body(..., description="License plate number for manual verification")
):
    """
    Manual backup access verification.
    """
    try:
        cleaned_plate = plate_number.upper().replace(" ", "")
        result = await DecisionEngine.evaluate_manual_access(
            token=token,
            manual_plate=cleaned_plate
        )

        return ManualAccessResponse(
            success=result["decision"] == "GRANTED",
            decision=result["decision"],
            token_valid=result["token_valid"],
            plate_match=result.get("plate_match"),
            recognized_plate=result.get("recognized_plate"),
            registered_plate=result.get("registered_plate"),
            timestamp=result.get("timestamp", datetime.utcnow()),
            message=result.get("message", ""),
            log_id=result.get("log_id")
        )

    except Exception as e:
        logger.error("Manual access verification failed", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Manual access verification failed due to internal error"
        )


@router.get("/status", response_model=AccessSystemStatusResponse)
async def get_access_system_status():
    """
    Returns the operational status of the access control system.
    Does not trigger model reloads; reads lazy-loaded models safely.
    """
    yolo_loaded = get_yolo_model() is not None
    ocr_loaded = get_ocr_reader() is not None

    system_status = "operational" if (yolo_loaded and ocr_loaded) else "degraded"

    return AccessSystemStatusResponse(
        status=system_status,
        two_factor_enabled=True,
        components={
            "token_service": "active",
            "anpr_service": "active" if (yolo_loaded and ocr_loaded) else "degraded",
            "decision_engine": "active"
        },
        message="Two-Factor Authentication system is operational" if system_status == "operational"
        else "System partially degraded: some components unavailable"
    )