"""
Camera Entry Router - Auto ANPR + Token Generation + Parking Allocation
New file: app/routers/camera_entry.py

Pipeline for every vehicle arrival:
  Image → ANPR (plate + colour) → Token auto-issued → Slot allocated → Logged
"""
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.services.anpr_service import ANPRService
from app.services.token_service import TokenService
from app.database import db

router = APIRouter(prefix="/camera-entry", tags=["Camera Entry"])


# ──────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────

class CameraEntryRequest(BaseModel):
    """
    Payload sent by the frontend when a vehicle is captured.
    image_base64 is the full data-URI string from canvas.toDataURL().
    user_id is optional — falls back to the registered owner of the vehicle.
    """
    image_base64: str
    user_id: Optional[str] = "auto_user"


class ManualEntryRequest(BaseModel):
    """
    Fallback: operator types the plate manually (e.g. camera unavailable).
    """
    plate_number: str
    vehicle_color: Optional[str] = "unknown"
    user_id: Optional[str] = "auto_user"


class ExitRequest(BaseModel):
    plate_number: str


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────

async def _build_entry_response(
    plate_number:   str,
    color:          str,
    color_hex:      str,
    color_confidence: float,
    anpr_confidence: Optional[float],
    processing_time_ms: float,
    user_id:        str,
) -> dict:
    """
    Shared logic used by both the camera endpoint and the manual endpoint:
      1. Check vehicle is registered
      2. Auto-generate JWT token
      3. Allocate parking slot
      4. Write camera-entry log
      5. Return structured response
    """

    # ── 1. Check vehicle registration ────────────────────────────────────
    vehicle = await db.get_vehicle_by_plate(plate_number)
    if not vehicle:
        return {
            "success":      False,
            "registered":   False,
            "plate_number": plate_number,
            "color":        color,
            "color_hex":    color_hex,
            "message":      f"Vehicle {plate_number} is NOT registered. "
                            f"Please register before entry.",
            "token":        None,
            "parking_slot": None,
            "parking_zone": None,
        }

    # ── 2. Auto-generate JWT token ────────────────────────────────────────
    resolved_user_id = vehicle.get("user_id", user_id)
    token_data = await TokenService.issue_token(
        user_id     = resolved_user_id,
        plate_number= plate_number,
        token_type  = "jwt",
        expiry_hours= 24,
    )

    # ── 3. Allocate parking slot ──────────────────────────────────────────
    slot = await db.get_available_slot()
    if slot:
        await db.occupy_slot(
            slot_id      = slot["slot_id"],
            plate_number = plate_number,
            token_id     = token_data["token_id"],
            vehicle_color= color,
        )
        parking_slot = slot["slot_id"]
        parking_zone = slot.get("zone", "A")
    else:
        parking_slot = None
        parking_zone = None

    # ── 4. Log the camera-entry event ─────────────────────────────────────
    await db.log_camera_entry({
        "plate_number":      plate_number,
        "color":             color,
        "color_hex":         color_hex,
        "color_confidence":  color_confidence,
        "anpr_confidence":   anpr_confidence,
        "token_id":          token_data["token_id"],
        "parking_slot":      parking_slot,
        "parking_zone":      parking_zone,
        "processing_time_ms": processing_time_ms,
        "timestamp":         datetime.utcnow(),
    })

    # Also mirror to the main access-log so the Logs page stays consistent
    await db.log_access_attempt({
        "plate_number":              plate_number,
        "token_id":                  token_data["token_id"],
        "access_decision":           "GRANTED",
        "token_valid":               True,
        "plate_recognized":          True,
        "plate_match":               True,
        "confidence":                anpr_confidence,
        "anpr_processing_time_ms":   processing_time_ms,
        "token_verification_time_ms": 0,
        "total_response_time_ms":    processing_time_ms,
        "timestamp":                 datetime.utcnow(),
    })

    # ── 5. Build response ─────────────────────────────────────────────────
    return {
        "success":        True,
        "registered":     True,
        "plate_number":   plate_number,
        "color":          color,
        "color_hex":      color_hex,
        "color_confidence": round(color_confidence * 100, 1),
        "anpr_confidence":  round((anpr_confidence or 0) * 100, 1),
        "processing_time_ms": round(processing_time_ms, 1),
        "token": {
            "token_id":     token_data["token_id"],
            "token_string": token_data["token_string"],
            "expiry_time":  token_data["expiry_time"].isoformat()
                            if hasattr(token_data["expiry_time"], "isoformat")
                            else str(token_data["expiry_time"]),
        },
        "parking_slot": parking_slot,
        "parking_zone": parking_zone,
        "message": (
            f"Entry granted — Slot {parking_slot} (Zone {parking_zone}) allocated."
            if parking_slot
            else "Entry granted — Car park is FULL, no slot available."
        ),
    }


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post("/process", response_model=dict, status_code=status.HTTP_200_OK)
async def process_camera_entry(request: CameraEntryRequest):
    """
    Main camera-entry endpoint.

    Accepts a base64 image from the frontend webcam capture.
    Runs the full pipeline:
      ANPR → colour detection → token generation → slot allocation → logging.

    Returns plate number, colour, generated token, and assigned parking slot.
    """
    if not request.image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_base64 is required",
        )

    # ── Run ANPR (plate + colour) ─────────────────────────────────────────
    try:
        anpr_result = await ANPRService.process_image(request.image_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ANPR processing error: {str(e)}",
        )

    # ANPR failed — return useful feedback but do NOT raise a 500
    if not anpr_result["success"]:
        return {
            "success":      False,
            "registered":   False,
            "plate_number": anpr_result.get("plate_number"),
            "color":        anpr_result.get("color", "unknown"),
            "color_hex":    anpr_result.get("color_hex", "#808080"),
            "message":      anpr_result.get("message", "Plate not detected"),
            "token":        None,
            "parking_slot": None,
            "parking_zone": None,
        }

    plate_number = anpr_result["plate_number"]

    return await _build_entry_response(
        plate_number     = plate_number,
        color            = anpr_result.get("color", "unknown"),
        color_hex        = anpr_result.get("color_hex", "#808080"),
        color_confidence = anpr_result.get("color_confidence", 0.0),
        anpr_confidence  = anpr_result.get("confidence"),
        processing_time_ms = anpr_result.get("processing_time_ms", 0),
        user_id          = request.user_id or "auto_user",
    )


@router.post("/manual", response_model=dict, status_code=status.HTTP_200_OK)
async def manual_camera_entry(request: ManualEntryRequest):
    """
    Fallback manual-entry endpoint.

    Used when the camera cannot read the plate (poor lighting, dirty plate, etc.)
    The operator types the plate number manually. Everything else (token
    generation, slot allocation, logging) is identical to the camera flow.
    """
    plate_number = request.plate_number.upper().replace(" ", "")

    if len(plate_number) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plate number must be at least 5 characters",
        )

    return await _build_entry_response(
        plate_number     = plate_number,
        color            = request.vehicle_color or "unknown",
        color_hex        = "#808080",
        color_confidence = 0.0,
        anpr_confidence  = None,    # no ANPR ran
        processing_time_ms = 0.0,
        user_id          = request.user_id or "auto_user",
    )


@router.post("/exit", response_model=dict, status_code=status.HTTP_200_OK)
async def process_exit(request: ExitRequest):
    """
    Vehicle exit endpoint.

    Releases the parking slot occupied by the given plate number.
    Should be called when the barrier opens on exit.
    """
    plate_number = request.plate_number.upper().replace(" ", "")

    released_slot = await db.release_slot(plate_number)

    if not released_slot:
        return {
            "success":      False,
            "plate_number": plate_number,
            "message":      f"No active parking record found for {plate_number}",
        }

    # Log the exit in the main access log
    await db.log_access_attempt({
        "plate_number":              plate_number,
        "token_id":                  "EXIT",
        "access_decision":           "GRANTED",
        "token_valid":               True,
        "plate_recognized":          True,
        "plate_match":               True,
        "confidence":                None,
        "anpr_processing_time_ms":   0,
        "token_verification_time_ms": 0,
        "total_response_time_ms":    0,
        "event_type":                "EXIT",
        "timestamp":                 datetime.utcnow(),
    })

    return {
        "success":        True,
        "plate_number":   plate_number,
        "released_slot":  released_slot,
        "message":        f"Exit recorded — {released_slot} is now free.",
    }


@router.get("/slots", response_model=dict)
async def get_parking_slots():
    """
    Return all parking slots with their current occupancy status.
    Used by the frontend to render the live parking grid.
    """
    summary = await db.get_parking_summary()

    # Strip MongoDB _id from each slot document
    for slot in summary["slots"]:
        slot.pop("_id", None)

    return {"success": True, **summary}


@router.get("/slots/available", response_model=dict)
async def get_available_slots():
    """
    Return only the unoccupied slots.
    Lightweight endpoint for quick availability checks.
    """
    all_slots = await db.get_all_slots()
    available = [s for s in all_slots if not s["is_occupied"]]
    for s in available:
        s.pop("_id", None)

    return {
        "success":   True,
        "available": len(available),
        "slots":     available,
    }


@router.get("/logs", response_model=dict)
async def get_camera_entry_logs(
    limit: int = Query(100, ge=1, le=500),
    skip:  int = Query(0,   ge=0),
):
    """
    Return camera-entry audit logs (most recent first).
    Separate from the main access-log; shows plate, colour,
    token issued, and slot allocated for each camera event.
    """
    logs = await db.get_camera_entry_logs(limit=limit, skip=skip)
    for log in logs:
        log["id"] = str(log.pop("_id"))

    return {
        "success": True,
        "count":   len(logs),
        "logs":    logs,
    }


@router.get("/logs/{plate_number}", response_model=dict)
async def get_entry_logs_by_plate(
    plate_number: str,
    limit: int = Query(20, ge=1, le=100),
):
    """
    Return camera-entry history for a specific vehicle plate.
    """
    plate = plate_number.upper().replace(" ", "")
    logs  = await db.get_camera_entry_by_plate(plate, limit=limit)
    for log in logs:
        log["id"] = str(log.pop("_id"))

    return {
        "success":      True,
        "plate_number": plate,
        "count":        len(logs),
        "logs":         logs,
    }


@router.get("/status", response_model=dict)
async def get_camera_entry_status():
    """
    Health-check for the camera-entry subsystem.
    Returns parking capacity and model readiness.
    """
    from app.services.anpr_service import get_yolo_model, get_ocr_reader

    summary    = await db.get_parking_summary()
    yolo_ready = get_yolo_model() is not None
    ocr_ready  = get_ocr_reader()  is not None

    return {
        "status":        "operational" if (yolo_ready and ocr_ready) else "degraded",
        "anpr_ready":    yolo_ready and ocr_ready,
        "yolo_loaded":   yolo_ready,
        "ocr_loaded":    ocr_ready,
        "parking": {
            "total":     summary["total"],
            "occupied":  summary["occupied"],
            "available": summary["available"],
        },
        "message": (
            "Camera entry system is fully operational"
            if (yolo_ready and ocr_ready)
            else "ANPR models not fully loaded — manual entry available as fallback"
        ),
    }