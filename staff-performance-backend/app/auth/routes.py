# app/auth/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore  # type: ignore

from app.auth.schemas import LoginRequest, LoginResponse, ChangePasswordRequest
from app.auth.service import authenticate_user
from app.common.firestore_client import get_db_dep
from app.common.security import get_current_user, hash_password, verify_password


router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: firestore.Client = Depends(get_db_dep),
) -> LoginResponse:
    """
    Login endpoint - returns JWT token on successful authentication.
    """
    ok, msg, token, role, user_data = authenticate_user(
        db, payload.email, payload.password
    )

    if not ok:
        return LoginResponse(
            success=False,
            message=msg,
            token=None,
            role=None,
            user=None
        )

    return LoginResponse(
        success=True,
        message=msg,
        token=token,
        role=role,
        user=user_data
    )


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
) -> dict:
    """
    Change password for the current logged-in user.
    Requires valid JWT token.
    """
    # Validate new password matches confirmation
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match"
        )
    
    # Validate new password is not empty and meets minimum requirements
    if len(payload.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long"
        )
    
    # Get user email from token
    email = current_user.get("email")
    
    # Find user in database
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", email).limit(1).stream()
    
    user_doc = None
    for doc in query:
        user_doc = doc
        break
    
    if user_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    data = user_doc.to_dict() or {}
    stored_password = data.get("password")
    
    # Verify old password
    password_valid = False
    try:
        if stored_password.startswith("$2b$") or stored_password.startswith("$2a$"):
            password_valid = verify_password(payload.old_password, stored_password)
        else:
            password_valid = (stored_password == payload.old_password)
    except Exception:
        password_valid = (stored_password == payload.old_password)
    
    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Hash and update new password
    hashed_password = hash_password(payload.new_password)
    user_doc.reference.update({"password": hashed_password})
    
    return {
        "success": True,
        "message": "Password changed successfully"
    }


@router.get("/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Get current logged-in user information from JWT token.
    Requires valid JWT token.
    """
    return {
        "success": True,
        "user": current_user
    }
