"""
CVT-VACS: Computer Vision and Token-Based Vehicle Access Control System
Main FastAPI Application Entry Point

Developed by: Daria Benjamin Francis (AUPG/24/0033)
Adeleke University, Ede, Osun State, Nigeria
Supervisor: Dr Onamade, A.A
Co-supervisor: Dr Oduwole, O. A.
"""
import os
import traceback
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import db

# ── Routers ──────────────────────────────────────────────────────────────────
from app.routers import vehicles, tokens, anpr, access, logs, camera_entry

settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and graceful shutdown
    """
    print("🚀 Starting CVT-VACS Server...")
    print(f"📁 Database : {settings.DATABASE_NAME}")
    print(f"🔐 Algorithm: {settings.ALGORITHM}")

    try:
        await db.connect()
        print("✅ Database connected successfully")
    except Exception as e:
        print("❌ Database connection failed:")
        traceback.print_exc()
        raise e

    print("✅ Server ready!")
    print("=" * 58)

    yield

    print("\n🛑 Shutting down CVT-VACS Server...")
    try:
        await db.disconnect()
    except Exception:
        pass
    print("👋 Goodbye!")


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## CVT-VACS: Two-Factor Authentication for Vehicle Access

Combines:
- **ANPR** – YOLOv8 + EasyOCR + colour detection
- **Token-based Auth** – JWT/QR/OTP
- **Camera Entry** – live capture → auto token → parking allocation

### Flow
1. Vehicle approaches
2. Camera captures image
3. ANPR detects plate & colour
4. JWT token issued
5. Parking slot allocated
6. Barrier opens → access granted

### API Sections
| Prefix | Description |
|---|---|
| `/vehicles` | Manage vehicles |
| `/tokens` | Issue/verify tokens |
| `/anpr` | Standalone ANPR |
| `/access` | 2FA access control |
| `/camera-entry` | Camera + parking |
| `/logs` | Audit logs & metrics |
""",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
origins = [
    "https://cvt-vacs.netlify.app",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(vehicles.router, prefix="/vehicles")
app.include_router(tokens.router, prefix="/tokens")
app.include_router(anpr.router, prefix="/anpr")
app.include_router(access.router, prefix="/access")
app.include_router(logs.router, prefix="/logs")
app.include_router(camera_entry.router, prefix="/camera-entry")

# ── Static files ──────────────────────────────────────────────────────────────
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Root / System Endpoints ───────────────────────────────────────────────────
@app.get("/", tags=["System"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "documentation": "/docs",
        "endpoints": {
            "vehicles": "/vehicles",
            "tokens": "/tokens",
            "anpr": "/anpr",
            "access": "/access",
            "camera_entry": "/camera-entry",
            "logs": "/logs",
        },
    }


@app.get("/health", tags=["System"])
async def health_check():
    try:
        from app.services.anpr_service import get_yolo_model, get_ocr_reader
        yolo_ready = get_yolo_model() is not None
        ocr_ready = get_ocr_reader() is not None
    except Exception:
        yolo_ready = False
        ocr_ready = False

    return {
        "status": "healthy",
        "database": "connected" if db.client else "disconnected",
        "anpr": {
            "yolo": "loaded" if yolo_ready else "not loaded",
            "ocr": "loaded" if ocr_ready else "not loaded",
            "ready": yolo_ready and ocr_ready,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/my-ip", tags=["System"])
async def get_my_ip():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.ipify.org?format=json")
            data = r.json()
            return {
                "server_ip": data.get("ip"),
                "instruction": "Add this IP to MongoDB Atlas → Network Access → Add IP Address",
            }
    except Exception as e:
        return {"error": str(e)}


@app.get("/system-info", tags=["System"])
async def system_info():
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug_mode": settings.DEBUG,
        "token_expiry_hours": settings.TOKEN_EXPIRY_HOURS,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        "plate_confidence_threshold": settings.PLATE_CONFIDENCE_THRESHOLD,
        "features": {
            "anpr_enabled": True,
            "colour_detection": True,
            "token_authentication": True,
            "two_factor_auth": True,
            "camera_entry": True,
            "parking_management": True,
            "audit_logging": True,
            "sms_notifications": bool(settings.TWILIO_ACCOUNT_SID),
        },
    }


# ── Dev entry-point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    PORT = int(os.environ.get("PORT", 8000))

    print(
        """
╔══════════════════════════════════════════════════════════╗
║           CVT-VACS Server Starting...                    ║
║                                                          ║
║  Computer Vision and Token-Based Vehicle Access Control  ║
║                                                          ║
║  Developed by: Daria Benjamin Francis                    ║
║  Matric No: AUPG/24/0033                                 ║
║  Adeleke University, Ede, Osun State                     ║
╚══════════════════════════════════════════════════════════╝
"""
    )

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=settings.DEBUG,
        log_level="info",
    )