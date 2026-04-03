"""
Vehicle Management API Routes
"""
from fastapi import APIRouter, HTTPException, status as http_status
from datetime import datetime

from app.models.schemas import VehicleCreate
from app.database import db

router = APIRouter(tags=["Vehicles"])


@router.post("/register", response_model=dict, status_code=http_status.HTTP_201_CREATED)
async def register_vehicle(vehicle: VehicleCreate):
    # Normalize plate early
    plate_number = vehicle.plate_number.upper().replace(" ", "")

    # Check if vehicle already exists
    existing = await db.get_vehicle_by_plate(plate_number)
    if existing:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Vehicle with plate {plate_number} already registered"
        )

    # ✅ HANDLE USER (Auto-create if not exists)
    user_id = vehicle.user_id

    if user_id:
        user = await db.get_user_by_id(user_id)

        if not user:
            # Auto-create user
            user_data = {
                "user_id": user_id,
                "created_at": datetime.utcnow()
            }
            await db.db.users.insert_one(user_data)
    else:
        # Optional: generate a default user_id if none provided
        user_id = f"user_{plate_number}"

        user = await db.get_user_by_id(user_id)
        if not user:
            user_data = {
                "user_id": user_id,
                "created_at": datetime.utcnow()
            }
            await db.db.users.insert_one(user_data)

    # Create vehicle
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
    plate_number = plate_number.upper().replace(" ", "")

    vehicle = await db.get_vehicle_by_plate(plate_number)

    if not vehicle:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with plate {plate_number} not found"
        )

    if "_id" in vehicle:
        vehicle["id"] = str(vehicle.pop("_id"))

    return {
        "success": True,
        "vehicle": vehicle
    }


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
    """
    Get all registered vehicles (with pagination)
    """

    if db.db is None:
        raise HTTPException(
            status_code=500,
            detail="Database not connected"
        )

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
    """
    Update vehicle access status (active/inactive/banned)
    """

    plate_number = plate_number.upper().replace(" ", "")
    status = status.lower()

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