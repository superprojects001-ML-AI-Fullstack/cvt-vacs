"""
MongoDB Database Connection and Operations (Async Motor)
Updated: Added parking slot management, camera entry support, and seed data
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

    # ──────────────────────────────
    # Safety Check
    # ──────────────────────────────
    @classmethod
    def check_db(cls):
        if cls.db is None:
            raise Exception("❌ Database not connected. Check MONGODB_URL.")

    # ──────────────────────────────
    # Connect / Disconnect
    # ──────────────────────────────
    @classmethod
    async def connect(cls):
        """Connect to MongoDB Atlas/Local"""
        try:
            if not settings.MONGODB_URL:
                raise ValueError("❌ MONGODB_URL is not set in environment variables")

            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            cls.db = cls.client[settings.DATABASE_NAME]

            # Force connection test
            await cls.client.admin.command("ping")

            # Create indexes and seed parking slots
            await cls._create_indexes()
            await cls.seed_parking_slots()

            print(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")

        except Exception as e:
            print(f"❌ MongoDB Connection Error: {e}")
            raise

    @classmethod
    async def disconnect(cls):
        """Disconnect from MongoDB"""
        if cls.client:
            cls.client.close()
            print("🔌 Disconnected from MongoDB")

    # ──────────────────────────────
    # Indexes
    # ──────────────────────────────
    @classmethod
    async def _create_indexes(cls):
        cls.check_db()

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
        await cls.db.parking_slots.create_index([("slot_id", ASCENDING)], unique=True)
        await cls.db.parking_slots.create_index([("is_occupied", ASCENDING)])
        await cls.db.parking_slots.create_index([("plate_number", ASCENDING)])

        # Camera entry logs collection
        await cls.db.camera_entry_logs.create_index([("timestamp", DESCENDING)])
        await cls.db.camera_entry_logs.create_index([("plate_number", ASCENDING)])

        print("📊 Database indexes created")

    # ──────────────────────────────
    # Seed Parking Slots
    # ──────────────────────────────
    @classmethod
    async def seed_parking_slots(cls):
        """Initialize default parking slots if none exist"""
        cls.check_db()
        count = await cls.db.parking_slots.count_documents({})
        if count == 0:
            slots = [{"slot_id": f"PS-{i+1}", "is_occupied": False} for i in range(50)]
            await cls.db.parking_slots.insert_many(slots)
            print("📌 Seeded parking slots")
        else:
            print(f"📌 Parking slots already seeded ({count} slots)")

    # ──────────────────────────────
# Parking Slot Operations
# ──────────────────────────────
@classmethod
async def get_parking_summary(cls) -> Dict[str, Any]:
    cls.check_db()
    
    total = await cls.db.parking_slots.count_documents({})
    occupied = await cls.db.parking_slots.count_documents({"is_occupied": True})
    available = total - occupied

    cursor = cls.db.parking_slots.find().sort("slot_id", ASCENDING)
    slots = await cursor.to_list(length=total)

    # Clean up MongoDB _id field
    for slot in slots:
        slot.pop("_id", None)

    return {
        "total": total,
        "occupied": occupied,
        "available": available,
        "slots": slots
    }

    # ──────────────────────────────
    # User Operations
    # ──────────────────────────────
    @classmethod
    async def create_user(cls, user_data: Dict[str, Any]) -> str:
        cls.check_db()
        result = await cls.db.users.insert_one(user_data)
        return str(result.inserted_id)

    @classmethod
    async def get_user_by_id(cls, user_id: str) -> Optional[Dict]:
        cls.check_db()
        return await cls.db.users.find_one({"user_id": user_id})

    @classmethod
    async def get_user_by_email(cls, email: str) -> Optional[Dict]:
        cls.check_db()
        return await cls.db.users.find_one({"email": email})

    # ──────────────────────────────
    # Vehicle Operations
    # ──────────────────────────────
    @classmethod
    async def create_vehicle(cls, vehicle_data: Dict[str, Any]) -> str:
        cls.check_db()
        result = await cls.db.vehicles.insert_one(vehicle_data)
        return str(result.inserted_id)

    @classmethod
    async def get_vehicle_by_plate(cls, plate_number: str) -> Optional[Dict]:
        cls.check_db()
        return await cls.db.vehicles.find_one({"plate_number": plate_number})

    @classmethod
    async def get_vehicles_by_user(cls, user_id: str) -> List[Dict]:
        cls.check_db()
        cursor = cls.db.vehicles.find({"user_id": user_id})
        return await cursor.to_list(length=100)

    @classmethod
    async def update_vehicle_status(cls, plate_number: str, status: str):
        cls.check_db()
        await cls.db.vehicles.update_one(
            {"plate_number": plate_number},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )

    # ──────────────────────────────
    # Token Operations
    # ──────────────────────────────
    @classmethod
    async def create_token(cls, token_data: Dict[str, Any]) -> str:
        cls.check_db()
        result = await cls.db.tokens.insert_one(token_data)
        return str(result.inserted_id)

    @classmethod
    async def get_token_by_id(cls, token_id: str) -> Optional[Dict]:
        cls.check_db()
        return await cls.db.tokens.find_one({"token_id": token_id})

    @classmethod
    async def revoke_token(cls, token_id: str):
        cls.check_db()
        await cls.db.tokens.update_one(
            {"token_id": token_id},
            {"$set": {"is_revoked": True, "revoked_at": datetime.utcnow()}}
        )

    @classmethod
    async def get_active_tokens_by_plate(cls, plate_number: str) -> List[Dict]:
        cls.check_db()
        cursor = cls.db.tokens.find({
            "plate_number": plate_number,
            "is_revoked": False,
            "expiry_time": {"$gt": datetime.utcnow()}
        })
        return await cursor.to_list(length=10)

    # ──────────────────────────────
    # Access Log Operations
    # ──────────────────────────────
    @classmethod
    async def log_access_attempt(cls, log_data: Dict[str, Any]) -> str:
        cls.check_db()
        result = await cls.db.access_logs.insert_one(log_data)
        return str(result.inserted_id)

    @classmethod
    async def get_access_logs(cls, limit: int = 100, skip: int = 0) -> List[Dict]:
        cls.check_db()
        cursor = (
            cls.db.access_logs.find()
            .sort("timestamp", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    @classmethod
    async def get_logs_by_plate(cls, plate_number: str, limit: int = 50) -> List[Dict]:
        cls.check_db()
        cursor = (
            cls.db.access_logs.find({"plate_number": plate_number})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    @classmethod
    async def get_logs_by_date_range(cls, start: datetime, end: datetime) -> List[Dict]:
        cls.check_db()
        cursor = cls.db.access_logs.find(
            {"timestamp": {"$gte": start, "$lte": end}}
        ).sort("timestamp", DESCENDING)
        return await cursor.to_list(length=1000)

    @classmethod
    async def get_statistics(cls) -> Dict[str, Any]:
        cls.check_db()

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
            "total_users": total_users,
            "total_vehicles": total_vehicles,
            "total_tokens_issued": total_tokens,
            "total_access_logs": total_access_logs,
            "today_attempts": today_attempts,
            "today_granted": today_granted,
            "today_denied": today_denied,
        }


# Global database instance
db = Database()