"""
Camera Entry Router - Auto ANPR + Token Generation + Parking Allocation
Updated: Auto-create users and vehicles for new entries
"""
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.services.anpr_service import ANPRService
from app.services.token_service import TokenService
from app.database import db

router = APIRouter(tags=["Camera Entry"])


# ──────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────

class CameraEntryRequest(BaseModel):
    image_base64: str
    user_id: Optional[str] = "auto_user"


class ManualEntryRequest(BaseModel):
    plate_number: str
    vehicle_color: Optional[str] = "unknown"
    user_id: Optional[str] = "auto_user"


class ExitRequest(BaseModel):
    plate_number: str


# ──────────────────────────────────────────────
# NEW: Auto-create helpers
# ──────────────────────────────────────────────

async def ensure_user_exists(user_id: str) -> bool:
    """
    Check if user exists, create if not
    Returns True if user exists or was created successfully
    """
    try:
        existing = await db.get_user_by_id(user_id)
        if existing:
            return True
        
        # Auto-create user with minimal info
        user_data = {
            "user_id": user_id,
            "email": f"{user_id}@cvt-vacs.auto",
            "name": f"Auto User {user_id}",
            "phone": "",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_auto_created": True
        }
        
        await db.create_user(user_data)
        print(f"✅ Auto-created user: {user_id}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create user {user_id}: {e}")
        return False


async def ensure_vehicle_exists(plate_number: str, color: str = "unknown", user_id: str = "auto_user") -> tuple[bool, Optional[dict]]:
    """
    Check if vehicle exists, auto-register if not
    Returns (success, vehicle_data)
    """
    try:
        # Check if vehicle exists
        existing = await db.get_vehicle_by_plate(plate_number)
        if existing:
            return True, existing
        
        # Ensure user exists first
        user_created = await ensure_user_exists(user_id)
        if not user_created:
            return False, None
        
        # Auto-register vehicle
        vehicle_data = {
            "plate_number": plate_number,
            "vehicle_type": "sedan",  # Default
            "make": "Unknown",
            "model": "Unknown",
            "color": color,
            "user_id": user_id,
            "registered_at": datetime.utcnow(),
            "status": "active",
            "last_access": None,
            "is_auto_registered": True
        }
        
        vehicle_id = await db.create_vehicle(vehicle_data)
        print(f"✅ Auto-registered vehicle: {plate_number} for user: {user_id}")
        
        # Return the created vehicle
        created = await db.get_vehicle_by_plate(plate_number)
        return True, created
        
    except Exception as e:
        print(f"❌ Failed to register vehicle {plate_number}: {e}")
        return False, None


# ──────────────────────────────────────────────
# Helper - Build entry response (MODIFIED)
# ──────────────────────────────────────────────

async def _build_entry_response(
    plate_number: str,
    color: str,
    color_hex: str,
    color_confidence: float,
    anpr_confidence: Optional[float],
    processing_time_ms: float,
    user_id: str,
) -> dict:

    plate_number = plate_number.upper().replace(" ", "")

    # 1. Check/Auto-create vehicle (and user) - MODIFIED
    vehicle_exists, vehicle = await ensure_vehicle_exists(plate_number, color, user_id)
    
    if not vehicle_exists or not vehicle:
        return {
            "success": False,
            "registered": False,
            "plate_number": plate_number,
            "color": color,
            "color_hex": color_hex,
            "message": f"Failed to auto-register vehicle {plate_number}. Please try again or use manual registration.",
            "token": None,
            "parking_slot": None,
            "parking_zone": None,
            "auto_registered": False
        }

    # 2. Token
    resolved_user_id = vehicle.get("user_id", user_id)

    token_data = await TokenService.issue_token(
        user_id=resolved_user_id,
        plate_number=plate_number,
        token_type="jwt",
        expiry_hours=24,
    )

    # 3. Parking
    slot = await db.get_available_slot()

    if slot:
        await db.occupy_slot(
            slot_id=slot["slot_id"],
            plate_number=plate_number,
            token_id=token_data["token_id"],
            vehicle_color=color,
        )
        parking_slot = slot["slot_id"]
        parking_zone = slot.get("zone", "A")
    else:
        parking_slot = None
        parking_zone = None

    # 4. Logs
    await db.log_camera_entry({
        "plate_number": plate_number,
        "color": color,
        "color_hex": color_hex,
        "color_confidence": color_confidence,
        "anpr_confidence": anpr_confidence,
        "token_id": token_data["token_id"],
        "parking_slot": parking_slot,
        "parking_zone": parking_zone,
        "processing_time_ms": processing_time_ms,
        "timestamp": datetime.utcnow(),
        "auto_registered": vehicle.get("is_auto_registered", False)
    })

    await db.log_access_attempt({
        "plate_number": plate_number,
        "token_id": token_data["token_id"],
        "access_decision": "GRANTED",
        "token_valid": True,
        "plate_recognized": True,
        "plate_match": True,
        "confidence": anpr_confidence,
        "anpr_processing_time_ms": processing_time_ms,
        "token_verification_time_ms": 0,
        "total_response_time_ms": processing_time_ms,
        "timestamp": datetime.utcnow(),
    })

    # 5. Response - MODIFIED to include auto_registered flag
    return {
        "success": True,
        "registered": True,
        "plate_number": plate_number,
        "color": color,
        "color_hex": color_hex,
        "color_confidence": round(color_confidence * 100, 1),
        "anpr_confidence": round((anpr_confidence or 0) * 100, 1),
        "processing_time_ms": round(processing_time_ms, 1),
        "token": {
            "token_id": token_data["token_id"],
            "token_string": token_data["token_string"],
            "expiry_time": (
                token_data["expiry_time"].isoformat()
                if hasattr(token_data["expiry_time"], "isoformat")
                else str(token_data["expiry_time"])
            ),
        },
        "parking_slot": parking_slot,
        "parking_zone": parking_zone,
        "message": (
            f"Entry granted — Slot {parking_slot} (Zone {parking_zone}) allocated."
            if parking_slot
            else "Entry granted — Car park is FULL, no slot available."
        ),
        "auto_registered": vehicle.get("is_auto_registered", False)
    }


# ──────────────────────────────────────────────
# Endpoints (unchanged)
# ──────────────────────────────────────────────

@router.post("/process", response_model=dict)
async def process_camera_entry(request: CameraEntryRequest):

    if not request.image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_base64 is required",
        )

    try:
        anpr_result = await ANPRService.process_image(request.image_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ANPR processing error: {str(e)}",
        )

    if not anpr_result["success"]:
        return {
            "success": False,
            "registered": False,
            "plate_number": anpr_result.get("plate_number"),
            "color": anpr_result.get("color", "unknown"),
            "color_hex": anpr_result.get("color_hex", "#808080"),
            "message": anpr_result.get("message", "Plate not detected"),
            "token": None,
            "parking_slot": None,
            "parking_zone": None,
            "auto_registered": False
        }

    return await _build_entry_response(
        plate_number=anpr_result["plate_number"],
        color=anpr_result.get("color", "unknown"),
        color_hex=anpr_result.get("color_hex", "#808080"),
        color_confidence=anpr_result.get("color_confidence", 0.0),
        anpr_confidence=anpr_result.get("confidence"),
        processing_time_ms=anpr_result.get("processing_time_ms", 0),
        user_id=request.user_id or "auto_user",
    )


@router.post("/manual", response_model=dict)
async def manual_camera_entry(request: ManualEntryRequest):

    plate_number = request.plate_number.upper().replace(" ", "")

    if len(plate_number) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plate number must be at least 5 characters",
        )

    return await _build_entry_response(
        plate_number=plate_number,
        color=request.vehicle_color or "unknown",
        color_hex="#808080",
        color_confidence=0.0,
        anpr_confidence=None,
        processing_time_ms=0.0,
        user_id=request.user_id or "auto_user",
    )


@router.post("/exit", response_model=dict)
async def process_exit(request: ExitRequest):

    plate_number = request.plate_number.upper().replace(" ", "")

    released_slot = await db.release_slot(plate_number)

    if not released_slot:
        return {
            "success": False,
            "plate_number": plate_number,
            "message": f"No active parking record found for {plate_number}",
        }

    await db.log_access_attempt({
        "plate_number": plate_number,
        "token_id": "EXIT",
        "access_decision": "GRANTED",
        "token_valid": True,
        "plate_recognized": True,
        "plate_match": True,
        "timestamp": datetime.utcnow(),
    })

    return {
        "success": True,
        "plate_number": plate_number,
        "released_slot": released_slot,
        "message": f"Exit recorded — {released_slot} is now free.",
    }


@router.get("/slots", response_model=dict)
async def get_parking_slots():

    summary = await db.get_parking_summary()

    for slot in summary["slots"]:
        slot.pop("_id", None)

    return {"success": True, **summary}


@router.get("/slots/available", response_model=dict)
async def get_available_slots():

    all_slots = await db.get_all_slots()
    available = [s for s in all_slots if not s["is_occupied"]]

    for s in available:
        s.pop("_id", None)

    return {
        "success": True,
        "available": len(available),
        "slots": available,
    }


@router.get("/logs", response_model=dict)
async def get_camera_entry_logs(
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
):

    logs = await db.get_camera_entry_logs(limit=limit, skip=skip)

    for log in logs:
        log["id"] = str(log.pop("_id"))

    return {
        "success": True,
        "count": len(logs),
        "logs": logs,
    }


@router.get("/logs/{plate_number}", response_model=dict)
async def get_entry_logs_by_plate(
    plate_number: str,
    limit: int = Query(20, ge=1, le=100),
):

    plate = plate_number.upper().replace(" ", "")
    logs = await db.get_camera_entry_by_plate(plate, limit=limit)

    for log in logs:
        log["id"] = str(log.pop("_id"))

    return {
        "success": True,
        "plate_number": plate,
        "count": len(logs),
        "logs": logs,
    }


@router.get("/status", response_model=dict)
async def get_camera_entry_status():

    from app.services.anpr_service import get_yolo_model, get_ocr_reader

    summary = await db.get_parking_summary()
    yolo_ready = get_yolo_model() is not None
    ocr_ready = get_ocr_reader() is not None

    return {
        "status": "operational" if (yolo_ready and ocr_ready) else "degraded",
        "anpr_ready": yolo_ready and ocr_ready,
        "yolo_loaded": yolo_ready,
        "ocr_loaded": ocr_ready,
        "parking": {
            "total": summary["total"],
            "occupied": summary["occupied"],
            "available": summary["available"],
        },
        "message": (
            "Camera entry system is fully operational"
            if (yolo_ready and ocr_ready)
            else "ANPR models not fully loaded — manual entry available"
        ),
    }