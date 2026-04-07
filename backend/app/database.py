"""
MongoDB Database Connection and Operations (Async Motor)
Updated: Fixed unique indexes with automatic conflict resolution
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure
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
    def check_db(self):
        if self.db is None:
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
    # Safe Index Creation Helper
    # ──────────────────────────────
    @classmethod
    async def _safe_create_index(cls, collection, keys, **kwargs):
        """
        Safely create an index, automatically handling conflicts by dropping 
        and recreating if the index exists with different specifications.
        """
        try:
            await collection.create_index(keys, **kwargs)
        except OperationFailure as e:
            error_msg = str(e).lower()
            # Check for index name conflict or key spec conflict
            if any(phrase in error_msg for phrase in [
                "indexkeyspecsconflict", 
                "same name as the requested index",
                "already exists with different options"
            ]):
                # Generate the index name that MongoDB would use
                if isinstance(keys, list):
                    name_parts = []
                    for field, direction in keys:
                        suffix = "1" if direction == ASCENDING else "-1"
                        name_parts.append(f"{field}_{suffix}")
                    index_name = "_".join(name_parts)
                else:
                    index_name = f"{keys}_1"
                
                # Use provided name if available
                index_name = kwargs.get("name", index_name)
                
                print(f"⚠️ Index conflict detected for '{index_name}' in '{collection.name}', fixing...")
                try:
                    await collection.drop_index(index_name)
                    await collection.create_index(keys, **kwargs)
                    print(f"✅ Index '{index_name}' recreated successfully")
                except Exception as drop_err:
                    print(f"⚠️ Could not fix index '{index_name}': {drop_err}")
                    # Don't raise - let the app continue with existing index
            else:
                # Re-raise if it's a different error
                raise e

    # ──────────────────────────────
    # Indexes
    # ──────────────────────────────
    @classmethod
    async def _create_indexes(cls):
        if cls.db is None:
            raise Exception("❌ Database not connected.")

        # Users collection
        await cls._safe_create_index(cls.db.users, [("user_id", ASCENDING)], unique=True)
        await cls._safe_create_index(
            cls.db.users, 
            [("email", ASCENDING)],
            unique=True,
            partialFilterExpression={"email": {"$exists": True}}
        )

        # Vehicles collection
        await cls._safe_create_index(cls.db.vehicles, [("plate_number", ASCENDING)], unique=True)
        await cls._safe_create_index(cls.db.vehicles, [("user_id", ASCENDING)])

        # Tokens collection
        await cls._safe_create_index(cls.db.tokens, [("token_id", ASCENDING)], unique=True)
        await cls._safe_create_index(cls.db.tokens, [("plate_number", ASCENDING)])
        await cls._safe_create_index(cls.db.tokens, [("expiry_time", ASCENDING)], expireAfterSeconds=0)

        # Access Logs collection
        await cls._safe_create_index(cls.db.access_logs, [("timestamp", DESCENDING)])
        await cls._safe_create_index(cls.db.access_logs, [("plate_number", ASCENDING)])
        await cls._safe_create_index(cls.db.access_logs, [("token_id", ASCENDING)])

        # Parking slots collection
        await cls._safe_create_index(cls.db.parking_slots, [("slot_id", ASCENDING)], unique=True)
        await cls._safe_create_index(cls.db.parking_slots, [("is_occupied", ASCENDING)])
        await cls._safe_create_index(cls.db.parking_slots, [("plate_number", ASCENDING)])

        # Camera entry logs collection
        await cls._safe_create_index(cls.db.camera_entry_logs, [("timestamp", DESCENDING)])
        await cls._safe_create_index(cls.db.camera_entry_logs, [("plate_number", ASCENDING)])

        print("📊 Database indexes created/verified")

    # ──────────────────────────────
    # Seed Parking Slots
    # ──────────────────────────────
    @classmethod
    async def seed_parking_slots(cls):
        """Initialize default parking slots if none exist"""
        if cls.db is None:
            raise Exception("❌ Database not connected.")

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
    async def get_parking_summary(self) -> Dict[str, Any]:
        self.check_db()

        total = await self.db.parking_slots.count_documents({})
        occupied = await self.db.parking_slots.count_documents({"is_occupied": True})
        available = total - occupied

        cursor = self.db.parking_slots.find().sort("slot_id", ASCENDING)
        slots = await cursor.to_list(length=total)
        for slot in slots:
            slot.pop("_id", None)

        return {
            "total": total,
            "occupied": occupied,
            "available": available,
            "slots": slots
        }

    async def get_available_slot(self) -> Optional[Dict]:
        self.check_db()
        slot = await self.db.parking_slots.find_one({"is_occupied": False})
        if slot:
            slot.pop("_id", None)
        return slot

    async def get_all_slots(self) -> List[Dict]:
        self.check_db()
        cursor = self.db.parking_slots.find().sort("slot_id", ASCENDING)
        slots = await cursor.to_list(length=100)
        for slot in slots:
            slot.pop("_id", None)
        return slots

    async def occupy_slot(self, slot_id: str, plate_number: str, token_id: str, vehicle_color: str = "unknown"):
        self.check_db()
        await self.db.parking_slots.update_one(
            {"slot_id": slot_id},
            {"$set": {
                "is_occupied": True,
                "plate_number": plate_number,
                "token_id": token_id,
                "vehicle_color": vehicle_color,
                "occupied_at": datetime.utcnow()
            }}
        )

    async def release_slot(self, plate_number: str) -> Optional[str]:
        self.check_db()
        result = await self.db.parking_slots.find_one_and_update(
            {"plate_number": plate_number, "is_occupied": True},
            {"$set": {
                "is_occupied": False,
                "plate_number": None,
                "token_id": None,
                "vehicle_color": None,
                "occupied_at": None
            }},
            return_document=True
        )
        return result["slot_id"] if result else None

    # ──────────────────────────────
    # Camera Entry Log Operations
    # ──────────────────────────────
    async def log_camera_entry(self, log_data: Dict[str, Any]) -> str:
        self.check_db()
        result = await self.db.camera_entry_logs.insert_one(log_data)
        return str(result.inserted_id)

    async def get_camera_entry_logs(self, limit: int = 100, skip: int = 0) -> List[Dict]:
        self.check_db()
        cursor = self.db.camera_entry_logs.find().sort("timestamp", DESCENDING).skip(skip).limit(limit)
        logs = await cursor.to_list(length=limit)
        for log in logs:
            if "_id" in log:
                log["_id"] = str(log["_id"])
        return logs

    async def get_camera_entry_by_plate(self, plate_number: str, limit: int = 20) -> List[Dict]:
        self.check_db()
        cursor = self.db.camera_entry_logs.find({"plate_number": plate_number}).sort("timestamp", DESCENDING).limit(limit)
        logs = await cursor.to_list(length=limit)
        for log in logs:
            if "_id" in log:
                log["_id"] = str(log["_id"])
        return logs

    # ──────────────────────────────
    # User Operations
    # ──────────────────────────────
    async def create_user(self, user_data: Dict[str, Any]) -> str:
        self.check_db()
        # Only include email if provided
        if "email" in user_data and not user_data["email"]:
            user_data.pop("email")
        result = await self.db.users.insert_one(user_data)
        return str(result.inserted_id)

    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        self.check_db()
        return await self.db.users.find_one({"user_id": user_id})

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        self.check_db()
        return await self.db.users.find_one({"email": email})

    # ──────────────────────────────
    # Vehicle Operations
    # ──────────────────────────────
    async def create_vehicle(self, vehicle_data: Dict[str, Any]) -> str:
        self.check_db()
        result = await self.db.vehicles.insert_one(vehicle_data)
        return str(result.inserted_id)

    async def get_vehicle_by_plate(self, plate_number: str) -> Optional[Dict]:
        self.check_db()
        return await self.db.vehicles.find_one({"plate_number": plate_number})

    async def get_vehicles_by_user(self, user_id: str) -> List[Dict]:
        self.check_db()
        cursor = self.db.vehicles.find({"user_id": user_id})
        return await cursor.to_list(length=100)

    async def update_vehicle_status(self, plate_number: str, status: str):
        self.check_db()
        await self.db.vehicles.update_one(
            {"plate_number": plate_number},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}}
        )

    # ──────────────────────────────
    # Token Operations
    # ──────────────────────────────
    async def create_token(self, token_data: Dict[str, Any]) -> str:
        self.check_db()
        result = await self.db.tokens.insert_one(token_data)
        return str(result.inserted_id)

    async def get_token_by_id(self, token_id: str) -> Optional[Dict]:
        self.check_db()
        return await self.db.tokens.find_one({"token_id": token_id})

    async def revoke_token(self, token_id: str):
        self.check_db()
        await self.db.tokens.update_one(
            {"token_id": token_id},
            {"$set": {"is_revoked": True, "revoked_at": datetime.utcnow()}}
        )

    async def get_active_tokens_by_plate(self, plate_number: str) -> List[Dict]:
        self.check_db()
        cursor = self.db.tokens.find({
            "plate_number": plate_number,
            "is_revoked": False,
            "expiry_time": {"$gt": datetime.utcnow()}
        })
        return await cursor.to_list(length=10)

    # ──────────────────────────────
    # Access Log Operations
    # ──────────────────────────────
    async def log_access_attempt(self, log_data: Dict[str, Any]) -> str:
        self.check_db()
        result = await self.db.access_logs.insert_one(log_data)
        return str(result.inserted_id)

    async def get_access_logs(self, limit: int = 100, skip: int = 0) -> List[Dict]:
        self.check_db()
        cursor = self.db.access_logs.find().sort("timestamp", DESCENDING).skip(skip).limit(limit)
        logs = await cursor.to_list(length=limit)
        for log in logs:
            if "_id" in log:
                log["_id"] = str(log["_id"])
        return logs

    async def get_logs_by_plate(self, plate_number: str, limit: int = 50) -> List[Dict]:
        self.check_db()
        cursor = self.db.access_logs.find({"plate_number": plate_number}).sort("timestamp", DESCENDING).limit(limit)
        logs = await cursor.to_list(length=limit)
        for log in logs:
            if "_id" in log:
                log["_id"] = str(log["_id"])
        return logs

    async def get_logs_by_date_range(self, start: datetime, end: datetime) -> List[Dict]:
        self.check_db()
        cursor = self.db.access_logs.find({"timestamp": {"$gte": start, "$lte": end}}).sort("timestamp", DESCENDING)
        logs = await cursor.to_list(length=1000)
        for log in logs:
            if "_id" in log:
                log["_id"] = str(log["_id"])
        return logs

    async def get_statistics(self) -> Dict[str, Any]:
        self.check_db()

        total_users       = await self.db.users.count_documents({})
        total_vehicles    = await self.db.vehicles.count_documents({})
        total_tokens      = await self.db.tokens.count_documents({})
        total_access_logs = await self.db.access_logs.count_documents({})

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        today_attempts = await self.db.access_logs.count_documents({"timestamp": {"$gte": today_start}})
        today_granted  = await self.db.access_logs.count_documents({"timestamp": {"$gte": today_start}, "access_decision": "GRANTED"})
        today_denied   = await self.db.access_logs.count_documents({"timestamp": {"$gte": today_start}, "access_decision": "DENIED"})

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