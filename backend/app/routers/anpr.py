"""
ANPR API Routes - Automatic Number Plate Recognition
"""
from fastapi import APIRouter, HTTPException, status, File, UploadFile
import base64

from app.models.schemas import ANPRRequest
from app.services.anpr_service import ANPRService

# ❗ FIX: REMOVE prefix
router = APIRouter(tags=["ANPR"])


@router.post("/recognize", response_model=dict)
async def recognize_plate(request: ANPRRequest):
    """
    Recognize license plate from base64 image
    """
    if not request.image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image provided"
        )

    try:
        result = await ANPRService.process_image(request.image_base64)

        return {
            "success": result["success"],
            "plate_number": result.get("plate_number"),
            "confidence": result.get("confidence"),
            "message": result.get("message"),
            "processing_time_ms": result.get("processing_time_ms"),
            "bounding_box": result.get("bounding_box")
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ANPR processing failed: {str(e)}"
        )


@router.post("/recognize-file", response_model=dict)
async def recognize_plate_from_file(file: UploadFile = File(...)):
    """
    Recognize license plate from uploaded image file
    """
    try:
        contents = await file.read()

        image_base64 = base64.b64encode(contents).decode("utf-8")
        image_base64 = f"data:image/jpeg;base64,{image_base64}"

        result = await ANPRService.process_image(image_base64)

        return {
            "success": result["success"],
            "plate_number": result.get("plate_number"),
            "confidence": result.get("confidence"),
            "message": result.get("message"),
            "processing_time_ms": result.get("processing_time_ms"),
            "bounding_box": result.get("bounding_box"),
            "filename": file.filename
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File processing failed: {str(e)}"
        )


@router.post("/validate", response_model=dict)
async def validate_plate_format(plate_number: str):
    """
    Validate license plate format
    """
    plate_number = plate_number.upper().replace(" ", "")

    is_valid, cleaned = ANPRService.validate_plate_format(plate_number)

    return {
        "valid": is_valid,
        "original": plate_number,
        "cleaned": cleaned,
        "message": "Valid plate format" if is_valid else "Invalid plate format"
    }


@router.get("/status", response_model=dict)
async def get_anpr_status():
    """
    Get ANPR service status
    """
    from app.services.anpr_service import get_yolo_model, get_ocr_reader

    yolo_loaded = get_yolo_model() is not None
    ocr_loaded = get_ocr_reader() is not None

    return {
        "status": "ready" if (yolo_loaded and ocr_loaded) else "degraded",
        "yolo_model": "loaded" if yolo_loaded else "not loaded",
        "ocr_reader": "loaded" if ocr_loaded else "not loaded",
        "message": (
            "ANPR service is ready"
            if (yolo_loaded and ocr_loaded)
            else "Some models failed to load"
        )
    }