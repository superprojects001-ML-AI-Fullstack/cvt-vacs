"""
Access Logs & System Statistics API Routes - Production Ready
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.database import db

# Configure logger
logger = logging.getLogger("access_logs")
logger.setLevel(logging.INFO)

# Router
router = APIRouter(tags=["Logs & Statistics"])


# ── Pydantic Models ────────────────────────────────────────────────
class AccessLogEntry(BaseModel):
    id: str
    plate_number: Optional[str] = None
    access_decision: Optional[str] = None
    token_valid: Optional[bool] = None
    recognized_plate: Optional[str] = None
    registered_plate: Optional[str] = None
    anpr_processing_time_ms: Optional[float] = None
    token_verification_time_ms: Optional[float] = None
    total_response_time_ms: Optional[float] = None
    timestamp: Optional[datetime] = None
    message: Optional[str] = None


class AccessLogResponse(BaseModel):
    success: bool
    count: int
    logs: List[AccessLogEntry]


class TodayLogResponse(AccessLogResponse):
    granted: int
    denied: int


class StatisticsResponse(BaseModel):
    success: bool
    statistics: dict


class PerformanceMetrics(BaseModel):
    anpr_accuracy: float
    anpr_precision: float
    anpr_recall: float
    anpr_f1_score: float
    token_verification_latency_ms: float
    system_response_time_ms: float
    authentication_success_rate: float
    throughput_vehicles_per_minute: float
    false_positive_rate: float
    false_negative_rate: float
    sample_size: int


class PerformanceResponse(BaseModel):
    success: bool
    metrics: PerformanceMetrics


class VehicleHistoryResponse(BaseModel):
    success: bool
    plate_number: str
    total_accesses: int
    granted: int
    denied: int
    history: List[AccessLogEntry]


# ── Helper Functions ───────────────────────────────────────────────
def sanitize_plate(plate: str) -> str:
    return plate.upper().replace(" ", "")


def transform_logs(raw_logs: list) -> List[dict]:
    """Convert raw MongoDB documents to API-friendly format"""
    transformed = []
    for log in raw_logs:
        log_entry = dict(log)
        if "_id" in log_entry:
            log_entry["id"] = str(log_entry.pop("_id"))
        transformed.append(log_entry)
    return transformed


# ── Endpoints ─────────────────────────────────────────────────────
@router.get("/access", response_model=AccessLogResponse)
async def get_access_logs(
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    plate_number: Optional[str] = None
):
    try:
        if plate_number:
            plate_number = sanitize_plate(plate_number)
            raw_logs = await db.get_logs_by_plate(plate_number, limit)
        else:
            raw_logs = await db.get_access_logs(limit, skip)

        logs = transform_logs(raw_logs)
        return AccessLogResponse(success=True, count=len(logs), logs=logs)

    except Exception as e:
        logger.exception("Failed to retrieve access logs")
        raise HTTPException(status_code=500, detail="Failed to retrieve access logs")


@router.get("/access/today", response_model=TodayLogResponse)
async def get_today_logs():
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        raw_logs = await db.get_logs_by_date_range(today_start, datetime.utcnow())
        logs = transform_logs(raw_logs)

        granted = sum(1 for log in logs if log.get("access_decision") == "GRANTED")
        denied = sum(1 for log in logs if log.get("access_decision") == "DENIED")

        return TodayLogResponse(
            success=True,
            count=len(logs),
            logs=logs,
            granted=granted,
            denied=denied
        )

    except Exception as e:
        logger.exception("Failed to retrieve today's logs")
        raise HTTPException(status_code=500, detail="Failed to retrieve today's logs")


@router.get("/statistics", response_model=StatisticsResponse)
async def get_system_statistics():
    try:
        stats = await db.get_statistics()
        return StatisticsResponse(success=True, statistics=stats)
    except Exception as e:
        logger.exception("Failed to retrieve system statistics")
        raise HTTPException(status_code=500, detail="Failed to retrieve system statistics")


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance_metrics():
    try:
        raw_logs = await db.get_access_logs(limit=1000)
        logs = transform_logs(raw_logs)

        if not logs:
            empty_metrics = PerformanceMetrics(
                anpr_accuracy=0.0,
                anpr_precision=0.0,
                anpr_recall=0.0,
                anpr_f1_score=0.0,
                token_verification_latency_ms=0.0,
                system_response_time_ms=0.0,
                authentication_success_rate=0.0,
                throughput_vehicles_per_minute=0.0,
                false_positive_rate=0.0,
                false_negative_rate=0.0,
                sample_size=0
            )
            return PerformanceResponse(success=True, metrics=empty_metrics)

        total = len(logs)

        # Safe calculations with .get() to avoid KeyError
        tp = sum(1 for log in logs 
                 if log.get("access_decision") == "GRANTED" and log.get("token_valid") is True)
        tn = sum(1 for log in logs 
                 if log.get("access_decision") == "DENIED" and log.get("token_valid") is False)
        fp = sum(1 for log in logs 
                 if log.get("access_decision") == "GRANTED" and log.get("token_valid") is False)
        fn = sum(1 for log in logs 
                 if log.get("access_decision") == "DENIED" and log.get("token_valid") is True)

        accuracy = (tp + tn) / total if total > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0

        # Safe extraction of numeric fields
        token_times = [log.get("token_verification_time_ms") 
                      for log in logs 
                      if isinstance(log.get("token_verification_time_ms"), (int, float))]
        total_times = [log.get("total_response_time_ms") 
                      for log in logs 
                      if isinstance(log.get("total_response_time_ms"), (int, float))]

        avg_token_time = sum(token_times) / len(token_times) if token_times else 0
        avg_total_time = sum(total_times) / len(total_times) if total_times else 0

        success_rate = (tp + tn) / total if total > 0 else 0

        # Safe timestamp filtering
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_logs = [
            log for log in logs
            if isinstance(log.get("timestamp"), datetime) and log.get("timestamp") > one_hour_ago
        ]
        throughput = len(recent_logs) / 60.0

        metrics = PerformanceMetrics(
            anpr_accuracy=round(accuracy * 100, 2),
            anpr_precision=round(precision * 100, 2),
            anpr_recall=round(recall * 100, 2),
            anpr_f1_score=round(f1 * 100, 2),
            token_verification_latency_ms=round(avg_token_time, 2),
            system_response_time_ms=round(avg_total_time, 2),
            authentication_success_rate=round(success_rate * 100, 2),
            throughput_vehicles_per_minute=round(throughput, 2),
            false_positive_rate=round(fpr * 100, 2),
            false_negative_rate=round(fnr * 100, 2),
            sample_size=total,
        )

        return PerformanceResponse(success=True, metrics=metrics)

    except Exception as e:
        logger.exception("Failed to calculate performance metrics")
        raise HTTPException(status_code=500, detail="Failed to calculate performance metrics")


@router.get("/plate/{plate_number}/history", response_model=VehicleHistoryResponse)
async def get_vehicle_access_history(
    plate_number: str,
    limit: int = Query(50, ge=1, le=200)
):
    try:
        plate_number = sanitize_plate(plate_number)
        raw_logs = await db.get_logs_by_plate(plate_number, limit)
        logs = transform_logs(raw_logs)

        granted = sum(1 for log in logs if log.get("access_decision") == "GRANTED")
        denied = sum(1 for log in logs if log.get("access_decision") == "DENIED")

        return VehicleHistoryResponse(
            success=True,
            plate_number=plate_number,
            total_accesses=len(logs),
            granted=granted,
            denied=denied,
            history=logs
        )

    except Exception as e:
        logger.exception(f"Failed to retrieve history for plate {plate_number}")
        raise HTTPException(status_code=500, detail="Failed to retrieve vehicle history")