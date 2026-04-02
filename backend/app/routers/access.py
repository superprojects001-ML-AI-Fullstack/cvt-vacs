"""
Access Control API Routes - Main 2FA Entry Point
"""
from fastapi import APIRouter, HTTPException, status, Body
from typing import Optional

from app.services.decision_engine import DecisionEngine

# ❗ FIX: remove prefix
router = APIRouter(tags=["Access Control"])


@router.post("/verify", response_model=dict)
async def verify_access(
    token: str = Body(...),
    image_base64: Optional[str] = Body(None),
    plate_number: Optional[str] = Body(None)
):
    """
    Two-Factor Authentication for Vehicle Access
    """

    if not image_base64 and not plate_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either image_base64 or plate_number must be provided"
        )

    try:
        result = await DecisionEngine.evaluate_access(
            token=token,
            image_base64=image_base64,
            detected_plate=plate_number
        )

        return {
            "success": result["decision"] == "GRANTED",
            "decision": result["decision"],
            "token_valid": result["token_valid"],
            "plate_recognized": result["plate_recognized"],
            "plate_match": result["plate_match"],
            "recognized_plate": result["recognized_plate"],
            "registered_plate": result.get("registered_plate"),
            "confidence": result["confidence"],
            "timestamp": result["timestamp"],
            "message": result["message"],
            "log_id": result["log_id"],
            "processing_times": result.get("processing_times", {})
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Access verification failed: {str(e)}"
        )


@router.post("/verify-manual", response_model=dict)
async def verify_access_manual(
    token: str = Body(...),
    plate_number: str = Body(...)
):
    """
    Manual access verification (backup)
    """
    try:
        result = await DecisionEngine.evaluate_manual_access(
            token=token,
            manual_plate=plate_number.upper().replace(" ", "")
        )

        return {
            "success": result["decision"] == "GRANTED",
            "decision": result["decision"],
            "token_valid": result["token_valid"],
            "plate_match": result["plate_match"],
            "recognized_plate": result["recognized_plate"],
            "registered_plate": result.get("registered_plate"),
            "timestamp": result["timestamp"],
            "message": result["message"],
            "log_id": result["log_id"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual verification failed: {str(e)}"
        )


@router.get("/status", response_model=dict)
async def get_access_system_status():
    """
    Get access control system status
    """
    from app.services.anpr_service import get_yolo_model, get_ocr_reader

    yolo_loaded = get_yolo_model() is not None
    ocr_loaded = get_ocr_reader() is not None

    return {
        "status": "operational" if (yolo_loaded and ocr_loaded) else "degraded",
        "2fa_enabled": True,
        "components": {
            "token_service": "active",
            "anpr_service": "active" if (yolo_loaded and ocr_loaded) else "degraded",
            "decision_engine": "active"
        },
        "message": "Two-Factor Authentication system is operational"
    }