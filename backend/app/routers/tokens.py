"""
Token Management API Routes
"""
from fastapi import APIRouter, HTTPException, status
from datetime import datetime

from app.models.schemas import TokenVerifyRequest
from app.services.token_service import TokenService
from app.database import db

# ❗ FIX: REMOVE prefix here
router = APIRouter(tags=["Tokens"])


@router.post("/issue", response_model=dict)
async def issue_token(
    user_id: str,
    plate_number: str,
    token_type: str = "jwt",
    expiry_hours: int = 24
):
    """
    Issue a new access token for a vehicle
    """
    try:
        # Normalize plate
        plate_number = plate_number.upper().replace(" ", "")

        token_data = await TokenService.issue_token(
            user_id=user_id,
            plate_number=plate_number,
            token_type=token_type,
            expiry_hours=expiry_hours
        )

        return {
            "success": True,
            "message": f"{token_type.upper()} token issued successfully",
            "token": {
                "token_id": token_data["token_id"],
                "token_string": token_data.get("token_string", token_data.get("qr_data")),
                "plate_number": token_data["plate_number"],
                "expiry_time": token_data["expiry_time"],
                "created_at": token_data["created_at"]
            }
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to issue token: {str(e)}"
        )


@router.post("/verify", response_model=dict)
async def verify_token(request: TokenVerifyRequest):
    """
    Verify a token's validity
    """
    result = TokenService.verify_jwt_token(request.token)

    return {
        "success": result["valid"],
        "valid": result["valid"],
        "token_id": result.get("token_id"),
        "plate_number": result.get("plate_number"),
        "message": result["message"]
    }


@router.post("/verify-with-plate", response_model=dict)
async def verify_token_with_plate(
    token: str,
    detected_plate: str
):
    """
    Verify token and check plate matching (for 2FA)
    """
    detected_plate = detected_plate.upper().replace(" ", "")

    result = await TokenService.verify_token_for_access(token, detected_plate)

    return {
        "success": result["access_granted"],
        "access_granted": result["access_granted"],
        "token_valid": result["token_valid"],
        "plate_match": result["plate_match"],
        "registered_plate": result.get("registered_plate"),
        "detected_plate": result.get("detected_plate"),
        "message": result["message"],
        "verification_time_ms": result["verification_time_ms"]
    }


@router.post("/revoke/{token_id}", response_model=dict)
async def revoke_token(token_id: str):
    """
    Revoke an active token
    """
    token = await db.get_token_by_id(token_id)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token {token_id} not found"
        )

    await db.revoke_token(token_id)

    return {
        "success": True,
        "message": f"Token {token_id} revoked successfully"
    }


@router.get("/active/{plate_number}", response_model=dict)
async def get_active_tokens(plate_number: str):
    """
    Get all active tokens for a vehicle
    """
    plate_number = plate_number.upper().replace(" ", "")

    tokens = await db.get_active_tokens_by_plate(plate_number)

    for token in tokens:
        token.pop("_id", None)
        token.pop("token_string", None)  # Hide sensitive data

    return {
        "success": True,
        "count": len(tokens),
        "tokens": tokens
    }


@router.get("/{token_id}", response_model=dict)
async def get_token_details(token_id: str):
    """
    Get token details by ID
    """
    token = await db.get_token_by_id(token_id)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token {token_id} not found"
        )

    token.pop("_id", None)

    expiry = token.get("expiry_time")
    is_expired = expiry < datetime.utcnow() if expiry else True

    return {
        "success": True,
        "token": {
            **token,
            "is_expired": is_expired
        }
    }