"""
ANPR API Routes - Automatic Number Plate Recognition
"""
from fastapi import APIRouter, HTTPException, status, File, UploadFile
import base64
from datetime import datetime
import re

from app.models.schemas import ANPRRequest
from app.services.anpr_service import ANPRService
from app.database import db

router = APIRouter(tags=["ANPR"])

# 🔹 Improved normalization to handle common variations
def normalize_plate(plate: str):
    if not plate:
        return None
    plate = plate.upper().replace(" ", "").replace("-", "")
    # Nigerian plates usually: ABC123DE or ABC-123-DE
    if len(plate) < 7 or len(plate) > 8:
        return None
    if len(plate) == 7:
        return f"{plate[:3]}-{plate[3:6]}-{plate[6:]}"  # ABC123DE → ABC-123-DE
    return f"{plate[:3]}-{plate[3:6]}-{plate[6:]}"      # ABC1234DE → ABC-123-4DE


# 🔹 Regex validation for standard Nigerian plate
PLATE_REGEX = r"^[A-Z]{3}-\d{3}-[A-Z0-9]{2,3}$"


async def save_plate_log(plate_number: str, confidence: float, source: str, raw_text: str):
    """Helper to save detected plate into ANPR logs"""
    await db.db.anpr_logs.insert_one({
        "plate_number": plate_number,
        "confidence": confidence,
        "detected_at": datetime.utcnow(),
        "source": source,
        "raw_text": raw_text
    })


@router.post("/recognize", response_model=dict)
async def recognize_plate(request: ANPRRequest):
    if not request.image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image provided"
        )
    try:
        result = await ANPRService.process_image(request.image_base64)
        plate_number = result.get("plate_number")

        if result["success"] and plate_number:
            normalized_plate = normalize_plate(plate_number)
            if normalized_plate and re.match(PLATE_REGEX, normalized_plate):
                await save_plate_log(normalized_plate, result.get("confidence", 0), "camera", plate_number)
                plate_number = normalized_plate
            else:
                plate_number = None  # OCR failed or plate format unexpected

        return {
            "success": result.get("success", False),
            "plate_number": plate_number,
            "confidence": result.get("confidence", 0),
            "message": result.get("message", "Recognition completed"),
            "processing_time_ms": result.get("processing_time_ms", 0),
            "bounding_box": result.get("bounding_box")
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ANPR processing failed: {str(e)}"
        )


@router.post("/recognize-file", response_model=dict)
async def recognize_plate_from_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image_base64 = f"data:image/jpeg;base64,{base64.b64encode(contents).decode('utf-8')}"
        result = await ANPRService.process_image(image_base64)

        plate_number = result.get("plate_number")

        if result["success"] and plate_number:
            normalized_plate = normalize_plate(plate_number)
            if normalized_plate and re.match(PLATE_REGEX, normalized_plate):
                await save_plate_log(normalized_plate, result.get("confidence", 0), file.filename, plate_number)
                plate_number = normalized_plate
            else:
                plate_number = None

        return {
            "success": result.get("success", False),
            "plate_number": plate_number,
            "confidence": result.get("confidence", 0),
            "message": result.get("message", "Recognition completed"),
            "processing_time_ms": result.get("processing_time_ms", 0),
            "bounding_box": result.get("bounding_box"),
            "filename": file.filename
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File processing failed: {str(e)}"
        )


@router.get("/detections", response_model=dict)
async def get_detected_plates(limit: int = 20):
    cursor = db.db.anpr_logs.find().sort("detected_at", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    for log in logs:
        log["id"] = str(log.pop("_id"))
    return {
        "success": True,
        "count": len(logs),
        "detections": logs
    }


@router.get("/status", response_model=dict)
async def get_anpr_status():
    from app.services.anpr_service import get_yolo_model, get_ocr_reader
    yolo_loaded = get_yolo_model() is not None
    ocr_loaded = get_ocr_reader() is not None

    return {
        "status": "ready" if (yolo_loaded and ocr_loaded) else "degraded",
        "yolo_model": "loaded" if yolo_loaded else "not loaded",
        "ocr_reader": "loaded" if ocr_loaded else "not loaded",
        "message": "ANPR service is ready" if (yolo_loaded and ocr_loaded) else "Some models failed to load"
    }