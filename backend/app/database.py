"""
MongoDB Database Connection and Operations (Async Motor)
Updated: Added parking slot management and camera entry support
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.config import get_settings

settings = get_settings()


class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None

        @classmethod
    async def connect(cls):
        """Connect to MongoDB Atlas/Local"""
        try:
            if not settings.MONGODB_URL:
                print("⚠️  MONGODB_URL not set, using localhost fallback")
                cls.client = AsyncIOMotorClient("mongodb://localhost:27017")
            else:
                cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            
            cls.db = cls.client[settings.DATABASE_NAME]

            # Create indexes and seed data
            await cls._create_indexes()
            await cls.seed_parking_slots()

            print(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")
        except Exception as e:
            print(f"❌ MongoDB Connection Error: {e}")
            print("⚠️  Continuing without database - some features will be disabled")
            # Don't raise - let the app start without DB for debugging
            cls.client = None
            cls.db = None
            
    @classmethod
    async def disconnect(cls):
        """Disconnect from MongoDB"""
        if cls.client:
            cls.client.close()
            print("🔌 Disconnected from MongoDB")

    @classmethod
    async def _create_indexes(cls):
        """Create database indexes for optimal performance"""
        # Users collection
        await cls.db.users.create_index([("user_id", ASCENDING)], unique=True)
        await cls.db.users.create_index([("email", ASCENDING)], unique=True)

        # Vehicles collection
        await cls.db.vehicles.create_index([("plate_number", ASCENDING)], unique=True)
        await cls.db.vehicles.create_index([("user_id", ASCENDING)])

        # Tokens collection
        await cls.db.tokens.create_index([("token_id", ASCENDING)], unique=True)
        await cls.db.tokens.create_index([("plate_number", ASCENDING)])
        await cls.db.tokens.create_index(
            [("expiry_time", ASCENDING)], expireAfterSeconds=0
        )

        # Access Logs collection
        await cls.db.access_logs.create_index([("timestamp", DESCENDING)])
        await cls.db.access_logs.create_index([("plate_number", ASCENDING)])
        await cls.db.access_logs.create_index([("token_id", ASCENDING)])

        # Parking slots collection
        await cls.db.parking_slots.create_index(
            [("slot_id", ASCENDING)], unique=True
        )
        await cls.db.parking_slots.create_index([("is_occupied", ASCENDING)])
        await cls.db.parking_slots.create_index([("plate_number", ASCENDING)])

        # Camera entry logs collection
        await cls.db.camera_entry_logs.create_index([("timestamp", DESCENDING)])
        await cls.db.camera_entry_logs.create_index([("plate_number", ASCENDING)])

        print("📊 Database indexes created")

    # ─────────────────────────────────────────────
    # User Operations  (unchanged)
    # ─────────────────────────────────────────────
    @classmethod
    async def create_user(cls, user_data: Dict[str, Any]) -> str:
        result = await cls.db.users.insert_one(user_data)
        return str(result.inserted_id)

    @classmethod
    async def get_user_by_id(cls, user_id: str) -> Optional[Dict]:
        return await cls.db.users.find_one({"user_id": user_id})

    @classmethod
    async def get_user_by_email(cls, email: str) -> Optional[Dict]:
        return await cls.db.users.find_one({"email": email})

    # ─────────────────────────────────────────────
    # Vehicle Operations  (unchanged)
    # ─────────────────────────────────────────────
    @classmethod
    async def create_vehicle(cls, vehicle_data: Dict[str, Any]) -> str:
        result = await cls.db.vehicles.insert_one(vehicle_data)
        return str(result.inserted_id)

    @classmethod
    async def get_vehicle_by_plate(cls, plate_number: str) -> Optional[Dict]:
        return await cls.db.vehicles.find_one({"plate_number": plate_number})

    @classmethod
    async def get_vehicles_by_user(cls, user_id: str) -> List[Dict]:
        cursor = cls.db.vehicles.find({"user_id": user_id})
        return await cursor.to_list(length=100)

    @classmethod
    async def update_vehicle_status(cls, plate_number: str, status: str):
        await cls.db.vehicles.update_one(
            {"plate_number": plate_number},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )

    # ─────────────────────────────────────────────
    # Token Operations  (unchanged)
    # ─────────────────────────────────────────────
    @classmethod
    async def create_token(cls, token_data: Dict[str, Any]) -> str:
        result = await cls.db.tokens.insert_one(token_data)
        return str(result.inserted_id)

    @classmethod
    async def get_token_by_id(cls, token_id: str) -> Optional[Dict]:
        return await cls.db.tokens.find_one({"token_id": token_id})

    @classmethod
    async def revoke_token(cls, token_id: str):
        await cls.db.tokens.update_one(
            {"token_id": token_id},
            {"$set": {"is_revoked": True, "revoked_at": datetime.utcnow()}}
        )

    @classmethod
    async def get_active_tokens_by_plate(cls, plate_number: str) -> List[Dict]:
        cursor = cls.db.tokens.find({
            "plate_number": plate_number,
            "is_revoked":   False,
            "expiry_time":  {"$gt": datetime.utcnow()}
        })
        return await cursor.to_list(length=10)

    # ─────────────────────────────────────────────
    # Access Log Operations  (unchanged)
    # ─────────────────────────────────────────────
    @classmethod
    async def log_access_attempt(cls, log_data: Dict[str, Any]) -> str:
        result = await cls.db.access_logs.insert_one(log_data)
        return str(result.inserted_id)

    @classmethod
    async def get_access_logs(cls, limit: int = 100, skip: int = 0) -> List[Dict]:
        cursor = (
            cls.db.access_logs.find()
            .sort("timestamp", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    @classmethod
    async def get_logs_by_plate(cls, plate_number: str, limit: int = 50) -> List[Dict]:
        cursor = (
            cls.db.access_logs.find({"plate_number": plate_number})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    @classmethod
    async def get_logs_by_date_range(
        cls, start: datetime, end: datetime
    ) -> List[Dict]:
        cursor = cls.db.access_logs.find(
            {"timestamp": {"$gte": start, "$lte": end}}
        ).sort("timestamp", DESCENDING)
        return await cursor.to_list(length=1000)

    @classmethod
    async def get_statistics(cls) -> Dict[str, Any]:
        total_users       = await cls.db.users.count_documents({})
        total_vehicles    = await cls.db.vehicles.count_documents({})
        total_tokens      = await cls.db.tokens.count_documents({})
        total_access_logs = await cls.db.access_logs.count_documents({})

        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_attempts = await cls.db.access_logs.count_documents(
            {"timestamp": {"$gte": today_start}}
        )
        today_granted = await cls.db.access_logs.count_documents(
            {"timestamp": {"$gte": today_start}, "access_decision": "GRANTED"}
        )
        today_denied = await cls.db.access_logs.count_documents(
            {"timestamp": {"$gte": today_start}, "access_decision": "DENIED"}
        )

        return {
            "total_users":         total_users,
            "total_vehicles":      total_vehicles,
            "total_tokens_issued": total_tokens,
            "total_access_logs":   total_access_logs,
            "today_attempts":      today_attempts,
            "today_granted":       today_granted,
            "today_denied":        today_denied,
        }

    # ─────────────────────────────────────────────
    # Parking Slot Operations  (NEW)
    # ─────────────────────────────────────────────

    @classmethod
    async def seed_parking_slots(cls, total_slots: int = 20) -> None:
        """
        Idempotent seed — creates parking slots only if they do not exist yet.
        Slots 01-10 → Zone A,  Slots 11-20 → Zone B.
        Safe to call on every startup; existing slots are never overwritten.
        """
        for i in range(1, total_slots + 1):
            slot_id = f"SLOT-{i:02d}"
            zone    = "A" if i <= 10 else "B"
            await cls.db.parking_slots.update_one(
                {"slot_id": slot_id},
                {
                    "$setOnInsert": {
                        "slot_id":     slot_id,
                        "zone":        zone,
                        "is_occupied": False,
                        "plate_number": None,
                        "vehicle_color": None,
                        "entry_time":  None,
                        "token_id":    None,
                    }
                },
                upsert=True,
            )
        print(f"🅿️  Parking slots ready ({total_slots} slots, Zone A + Zone B)")

    @classmethod
    async def get_available_slot(cls) -> Optional[Dict]:
        """
        Return the first unoccupied slot (lowest slot number).
        Returns None when the car park is full.
        """
        return await cls.db.parking_slots.find_one(
            {"is_occupied": False},
            sort=[("slot_id", ASCENDING)],
        )

    @classmethod
    async def occupy_slot(
        cls,
        slot_id:      str,
        plate_number: str,
        token_id:     str  = "",
        vehicle_color: str = "unknown",
    ) -> None:
        """
        Mark a slot as occupied and record entry metadata.

        Args:
            slot_id:       e.g. "SLOT-03"
            plate_number:  cleaned plate string
            token_id:      the auto-generated token ID for this entry
            vehicle_color: colour detected by ANPR
        """
        await cls.db.parking_slots.update_one(
            {"slot_id": slot_id},
            {
                "$set": {
                    "is_occupied":   True,
                    "plate_number":  plate_number,
                    "vehicle_color": vehicle_color,
                    "entry_time":    datetime.utcnow(),
                    "token_id":      token_id,
                }
            },
        )

    @classmethod
    async def release_slot(cls, plate_number: str) -> Optional[str]:
        """
        Free the slot occupied by the given plate number.
        Returns the slot_id that was released, or None if not found.
        """
        slot = await cls.db.parking_slots.find_one({"plate_number": plate_number})
        if not slot:
            return None

        await cls.db.parking_slots.update_one(
            {"plate_number": plate_number},
            {
                "$set": {
                    "is_occupied":   False,
                    "plate_number":  None,
                    "vehicle_color": None,
                    "entry_time":    None,
                    "token_id":      None,
                    "exit_time":     datetime.utcnow(),
                }
            },
        )
        return slot["slot_id"]

    @classmethod
    async def get_slot_by_plate(cls, plate_number: str) -> Optional[Dict]:
        """Return the slot currently occupied by the given plate."""
        return await cls.db.parking_slots.find_one({"plate_number": plate_number})

    @classmethod
    async def get_all_slots(cls) -> List[Dict]:
        """Return all parking slots sorted by slot_id."""
        cursor = cls.db.parking_slots.find().sort("slot_id", ASCENDING)
        return await cursor.to_list(length=200)

    @classmethod
    async def get_parking_summary(cls) -> Dict[str, Any]:
        """
        Quick summary used by the camera-entry /slots endpoint.
        """
        all_slots  = await cls.get_all_slots()
        occupied   = [s for s in all_slots if s["is_occupied"]]
        available  = [s for s in all_slots if not s["is_occupied"]]
        zone_a_avail = [s for s in available if s.get("zone") == "A"]
        zone_b_avail = [s for s in available if s.get("zone") == "B"]

        return {
            "total":          len(all_slots),
            "occupied":       len(occupied),
            "available":      len(available),
            "zone_a_available": len(zone_a_avail),
            "zone_b_available": len(zone_b_avail),
            "slots":          all_slots,
        }

    # ─────────────────────────────────────────────
    # Camera Entry Log Operations  (NEW)
    # ─────────────────────────────────────────────

    @classmethod
    async def log_camera_entry(cls, entry_data: Dict[str, Any]) -> str:
        """
        Persist a camera-entry event (plate detected, token issued,
        slot allocated) as a separate audit document.

        Expected fields in entry_data:
            plate_number, color, confidence, token_id, token_string,
            parking_slot, parking_zone, processing_time_ms, timestamp
        """
        result = await cls.db.camera_entry_logs.insert_one(entry_data)
        return str(result.inserted_id)

    @classmethod
    async def get_camera_entry_logs(
        cls, limit: int = 100, skip: int = 0
    ) -> List[Dict]:
        cursor = (
            cls.db.camera_entry_logs.find()
            .sort("timestamp", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    @classmethod
    async def get_camera_entry_by_plate(
        cls, plate_number: str, limit: int = 20
    ) -> List[Dict]:
        cursor = (
            cls.db.camera_entry_logs.find({"plate_number": plate_number})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)


# Global database instance
db = Database()