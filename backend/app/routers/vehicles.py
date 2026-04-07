"""
Vehicle Management API Routes (CLEANED - NO EMAIL DEPENDENCY)
"""
from fastapi import APIRouter, HTTPException, status as http_status
from datetime import datetime
import re

from app.models.schemas import VehicleCreate
from app.database import db

router = APIRouter(tags=["Vehicles"])

# 🔹 Updated plate regex to match ANPR normalization
PLATE_REGEX = r"^[A-Z]{3}-\d{3}-[A-Z0-9]{2,3}$"

# 🔹 Robust plate normalization
def normalize_plate(plate: str):
    if not plate:
        return None
    plate = plate.upper().replace(" ", "").replace("-", "")
    if len(plate) < 7 or len(plate) > 8:
        return None
    return f"{plate[:3]}-{plate[3:6]}-{plate[6:]}"


@router.post("/register", response_model=dict, status_code=http_status.HTTP_201_CREATED)
async def register_vehicle(vehicle: VehicleCreate):
    # ✅ Normalize plate
    plate_number = normalize_plate(vehicle.plate_number)
    if not plate_number:
        raise HTTPException(
            status_code=400,
            detail="Invalid plate format length"
        )

    # ✅ Validate format
    if not re.match(PLATE_REGEX, plate_number):
        raise HTTPException(
            status_code=400,
            detail="Invalid plate format. Expected format: ABC-123-XY"
        )

    # 🔹 Optional: Check if plate exists in ANPR logs
    detected_plate = await db.db.anpr_logs.find_one({"plate_number": plate_number})
    if not detected_plate:
        print(f"[WARN] Plate {plate_number} not found in ANPR detection records")
        # Optional strict enforcement:
        # raise HTTPException(status_code=400, detail="Plate not found in ANPR detection records")

    # ✅ Check duplicate vehicle
    existing = await db.get_vehicle_by_plate(plate_number)
    if existing:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Vehicle with plate {plate_number} already registered"
        )

    # ✅ Handle user (NO EMAIL INVOLVED)
    user_id = vehicle.user_id or f"user_{plate_number}"

    user = await db.get_user_by_id(user_id)
    if not user:
        user_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow()
        }

        # 🔥 SAFETY: Ensure no email field is present
        user_data.pop("email", None)

        await db.db.users.insert_one(user_data)

    # ✅ Create vehicle
    vehicle_data = {
        "plate_number": plate_number,
        "vehicle_type": vehicle.vehicle_type,
        "make": vehicle.make,
        "model": vehicle.model,
        "color": vehicle.color,
        "user_id": user_id,
        "registered_at": datetime.utcnow(),
        "status": "active",
        "last_access": None
    }

    vehicle_id = await db.create_vehicle(vehicle_data)

    return {
        "success": True,
        "message": "Vehicle registered successfully",
        "vehicle_id": vehicle_id,
        "plate_number": plate_number,
        "user_id": user_id
    }


@router.get("/plate/{plate_number}", response_model=dict)
async def get_vehicle_by_plate(plate_number: str):
    plate_number = normalize_plate(plate_number)
    if not plate_number:
        raise HTTPException(status_code=400, detail="Invalid plate format")

    vehicle = await db.get_vehicle_by_plate(plate_number)
    if not vehicle:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with plate {plate_number} not found"
        )

    if "_id" in vehicle:
        vehicle["id"] = str(vehicle.pop("_id"))

    return {"success": True, "vehicle": vehicle}


@router.get("/user/{user_id}", response_model=dict)
async def get_user_vehicles(user_id: str):
    vehicles = await db.get_vehicles_by_user(user_id)

    for v in vehicles:
        if "_id" in v:
            v["id"] = str(v.pop("_id"))

    return {
        "success": True,
        "count": len(vehicles),
        "vehicles": vehicles
    }


@router.get("/all", response_model=dict)
async def get_all_vehicles(limit: int = 100, skip: int = 0):
    if db.db is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    cursor = db.db.vehicles.find().skip(skip).limit(limit)
    vehicles = await cursor.to_list(length=limit)

    for v in vehicles:
        if "_id" in v:
            v["id"] = str(v.pop("_id"))

    return {
        "success": True,
        "count": len(vehicles),
        "vehicles": vehicles
    }


@router.patch("/status/{plate_number}", response_model=dict)
async def update_vehicle_status(plate_number: str, status: str):
    plate_number = normalize_plate(plate_number)
    status = status.lower()

    if not plate_number:
        raise HTTPException(status_code=400, detail="Invalid plate format")

    valid_statuses = ["active", "inactive", "banned", "suspended"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    vehicle = await db.get_vehicle_by_plate(plate_number)
    if not vehicle:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with plate {plate_number} not found"
        )

    await db.update_vehicle_status(plate_number, status)

    return {
        "success": True,
        "message": f"Vehicle status updated to {status}",
        "plate_number": plate_number,
        "status": status
    }