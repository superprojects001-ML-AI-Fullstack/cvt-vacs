"""
CVT-VACS: Computer Vision and Token-Based Vehicle Access Control System
Main FastAPI Application Entry Point

Developed by: Daria Benjamin Francis (AUPG/24/0033)
Adeleke University, Ede, Osun State, Nigeria
Supervisor: Dr Onamade, A.A
Co-supervisor: Dr Oduwole, O. A.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import datetime
import os
import traceback

from app.config import get_settings
from app.database import db

# ── Routers ──────────────────────────────────────────────────────────────────
from app.routers import vehicles, tokens, anpr, access, logs, camera_entry

settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup (DB connect, parking seed) and graceful shutdown.
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
## Computer Vision and Token-Based Authentication System for Vehicle Access Control

This API implements a **Two-Factor Authentication (2FA)** system combining:
- **ANPR** – Automatic Number Plate Recognition (YOLOv8 + EasyOCR) with vehicle colour detection
- **Token-based Authentication** – JWT / QR / OTP tokens for secure credential verification
- **Camera Entry** – live webcam capture → auto token generation → parking slot allocation

### Authentication Flow
1. Vehicle approaches the access point
2. Camera captures the vehicle image
3. ANPR detects the licence plate **and** vehicle colour
4. A JWT token is automatically issued for that plate
5. A parking slot is allocated and the event is logged
6. Barrier opens — access granted

### API Sections
| Prefix | Description |
|---|---|
| `/vehicles` | Register & manage vehicles |
| `/tokens` | Issue & verify tokens manually |
| `/anpr` | Standalone ANPR processing |
| `/access` | 2FA access-control decision engine |
| `/camera-entry` | **New** — camera pipeline, parking, exit |
| `/logs` | Audit logs & performance metrics |
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cvt-vacs.netlify.app",
        "http://localhost:5173",
    ],
    allow_origin_regex="https://.*\\.netlify\\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(vehicles.router)
app.include_router(tokens.router)
app.include_router(anpr.router)
app.include_router(access.router)
app.include_router(logs.router)
app.include_router(camera_entry.router)


# ── Static files ──────────────────────────────────────────────────────────────
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Root endpoints ────────────────────────────────────────────────────────────

@app.get("/", tags=["System"])
async def root():
    """API information and available endpoints."""
    return {
        "name":          settings.APP_NAME,
        "version":       settings.APP_VERSION,
        "status":        "operational",
        "documentation": "/docs",
        "endpoints": {
            "vehicles":     "/vehicles",
            "tokens":       "/tokens",
            "anpr":         "/anpr",
            "access":       "/access",
            "camera_entry": "/camera-entry",
            "logs":         "/logs",
        },
    }


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    Returns database connectivity status and current UTC timestamp.
    """
    try:
        from app.services.anpr_service import get_yolo_model, get_ocr_reader
        yolo_ready = get_yolo_model() is not None
        ocr_ready  = get_ocr_reader()  is not None
    except Exception:
        yolo_ready = False
        ocr_ready  = False

    return {
        "status":    "healthy",
        "database":  "connected" if db.client else "disconnected",
        "anpr": {
            "yolo":  "loaded" if yolo_ready else "not loaded",
            "ocr":   "loaded" if ocr_ready  else "not loaded",
            "ready": yolo_ready and ocr_ready,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/my-ip", tags=["System"])
async def get_my_ip():
    """
    Returns the outbound IP address of this server.
    Use this to find Render's IP and whitelist it in MongoDB Atlas.
    ⚠️ Remove this endpoint after whitelisting is done.
    """
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.ipify.org?format=json")
            data = r.json()
            return {
                "server_ip": data.get("ip"),
                "instruction": "Add this IP to MongoDB Atlas → Network Access → Add IP Address"
            }
    except Exception as e:
        return {"error": str(e)}


@app.get("/system-info", tags=["System"])
async def system_info():
    """
    System configuration overview.
    Useful for verifying deployed settings without exposing secrets.
    """
    return {
        "app_name":                   settings.APP_NAME,
        "version":                    settings.APP_VERSION,
        "debug_mode":                 settings.DEBUG,
        "token_expiry_hours":         settings.TOKEN_EXPIRY_HOURS,
        "confidence_threshold":       settings.CONFIDENCE_THRESHOLD,
        "plate_confidence_threshold": settings.PLATE_CONFIDENCE_THRESHOLD,
        "features": {
            "anpr_enabled":         True,
            "colour_detection":     True,
            "token_authentication": True,
            "two_factor_auth":      True,
            "camera_entry":         True,
            "parking_management":   True,
            "audit_logging":        True,
            "sms_notifications":    bool(settings.TWILIO_ACCOUNT_SID),
        },
    }


# ── Dev entry-point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║           CVT-VACS Server Starting...                    ║
    ║                                                          ║
    ║  Computer Vision and Token-Based Vehicle Access Control  ║
    ║                                                          ║
    ║  Developed by: Daria Benjamin Francis                    ║
    ║  Matric No: AUPG/24/0033                                 ║
    ║  Adeleke University, Ede, Osun State                     ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )