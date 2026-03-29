"""
Access Logs and Statistics API Routes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta

from app.database import db

router = APIRouter(prefix="/logs", tags=["Logs & Statistics"])


@router.get("/access", response_model=dict)
async def get_access_logs(
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    plate_number: Optional[str] = None
):
    """
    Get access logs with pagination
    
    Args:
        limit: Number of logs to return
        skip: Number of logs to skip
        plate_number: Filter by plate number (optional)
    """
    try:
        if plate_number:
            logs = await db.get_logs_by_plate(plate_number, limit)
        else:
            logs = await db.get_access_logs(limit, skip)
        
        # Convert ObjectIds to strings
        for log in logs:
            log["id"] = str(log.pop("_id"))
        
        return {
            "success": True,
            "count": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve logs: {str(e)}"
        )


@router.get("/access/today", response_model=dict)
async def get_today_logs():
    """
    Get today's access logs
    """
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        logs = await db.get_logs_by_date_range(today_start, datetime.utcnow())
        
        # Convert ObjectIds to strings
        for log in logs:
            log["id"] = str(log.pop("_id"))
        
        # Calculate statistics
        granted = sum(1 for log in logs if log.get("access_decision") == "GRANTED")
        denied = sum(1 for log in logs if log.get("access_decision") == "DENIED")
        
        return {
            "success": True,
            "count": len(logs),
            "granted": granted,
            "denied": denied,
            "logs": logs
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve today's logs: {str(e)}"
        )


@router.get("/statistics", response_model=dict)
async def get_system_statistics():
    """
    Get system-wide statistics
    """
    try:
        stats = await db.get_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@router.get("/performance", response_model=dict)
async def get_performance_metrics():
    """
    Calculate system performance metrics
    """
    try:
        # Get recent logs for analysis
        logs = await db.get_access_logs(limit=1000)
        
        if not logs:
            return {
                "success": True,
                "metrics": {
                    "message": "Insufficient data for metrics calculation"
                }
            }
        
        # Calculate metrics
        total = len(logs)
        tp = sum(1 for log in logs if log.get("access_decision") == "GRANTED" and log.get("token_valid"))
        tn = sum(1 for log in logs if log.get("access_decision") == "DENIED" and not log.get("token_valid"))
        fp = sum(1 for log in logs if log.get("access_decision") == "GRANTED" and not log.get("token_valid"))
        fn = sum(1 for log in logs if log.get("access_decision") == "DENIED" and log.get("token_valid"))
        
        # Accuracy
        accuracy = (tp + tn) / total if total > 0 else 0
        
        # Precision
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        
        # Recall
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        # F1 Score
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # False Positive Rate
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        
        # False Negative Rate
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
        
        # Average processing times
        anpr_times = [log.get("anpr_processing_time_ms", 0) for log in logs if log.get("anpr_processing_time_ms")]
        token_times = [log.get("token_verification_time_ms", 0) for log in logs if log.get("token_verification_time_ms")]
        total_times = [log.get("total_response_time_ms", 0) for log in logs if log.get("total_response_time_ms")]
        
        avg_anpr_time = sum(anpr_times) / len(anpr_times) if anpr_times else 0
        avg_token_time = sum(token_times) / len(token_times) if token_times else 0
        avg_total_time = sum(total_times) / len(total_times) if total_times else 0
        
        # Authentication success rate
        success_rate = (tp + tn) / total if total > 0 else 0
        
        # Throughput (vehicles per minute based on last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_logs = [log for log in logs if log.get("timestamp", datetime.min) > one_hour_ago]
        throughput = len(recent_logs) / 60  # per minute
        
        return {
            "success": True,
            "metrics": {
                "anpr_accuracy": round(accuracy * 100, 2),
                "anpr_precision": round(precision * 100, 2),
                "anpr_recall": round(recall * 100, 2),
                "anpr_f1_score": round(f1 * 100, 2),
                "token_verification_latency_ms": round(avg_token_time, 2),
                "system_response_time_ms": round(avg_total_time, 2),
                "authentication_success_rate": round(success_rate * 100, 2),
                "throughput_vehicles_per_minute": round(throughput, 2),
                "false_positive_rate": round(fpr * 100, 2),
                "false_negative_rate": round(fnr * 100, 2),
                "sample_size": total
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate metrics: {str(e)}"
        )


@router.get("/plate/{plate_number}/history", response_model=dict)
async def get_vehicle_access_history(
    plate_number: str,
    limit: int = Query(50, ge=1, le=200)
):
    """
    Get access history for a specific vehicle
    """
    try:
        logs = await db.get_logs_by_plate(plate_number, limit)
        
        # Convert ObjectIds to strings
        for log in logs:
            log["id"] = str(log.pop("_id"))
        
        # Calculate vehicle-specific stats
        granted = sum(1 for log in logs if log.get("access_decision") == "GRANTED")
        denied = sum(1 for log in logs if log.get("access_decision") == "DENIED")
        
        return {
            "success": True,
            "plate_number": plate_number,
            "total_accesses": len(logs),
            "granted": granted,
            "denied": denied,
            "history": logs
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve vehicle history: {str(e)}"
        )
