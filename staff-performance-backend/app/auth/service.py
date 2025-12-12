# app/auth/service.py
from typing import Optional
from google.cloud import firestore  # type: ignore
from app.common.security import verify_password, create_access_token


def authenticate_user(
    db: firestore.Client,
    email: str,
    password: str,
) -> tuple[bool, str, Optional[str], Optional[str], Optional[dict]]:
    """
    Authenticate user and return JWT token.
    
    Returns:
        Tuple of (success, message, token, role, user_data)
    """
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", email).limit(1).stream()

    user_doc = None
    for doc in query:
        user_doc = doc
        break

    if user_doc is None:
        return False, "User not found", None, None, None

    data = user_doc.to_dict() or {}
    
    # Get stored password (could be hashed or plain text for backward compatibility)
    stored_password = data.get("password")
    if not stored_password:
        return False, "Invalid user data", None, None, None
    
    # Try to verify as hashed password first, fall back to plain text comparison
    password_valid = False
    try:
        # Check if it's a hashed password (bcrypt hashes start with $2b$)
        if stored_password.startswith("$2b$") or stored_password.startswith("$2a$"):
            password_valid = verify_password(password, stored_password)
        else:
            # Plain text comparison (for existing users)
            password_valid = (stored_password == password)
    except Exception:
        # If verification fails, try plain text
        password_valid = (stored_password == password)
    
    if not password_valid:
        return False, "Invalid password", None, None, None
    
    # Get user details
    role = data.get("role", "employee")
    employee_id = data.get("employeeId", "")
    name = data.get("name", "")
    phone = data.get("phone", "")
    status = data.get("status", "active")
    
    # Check if account is active
    if status != "active":
        return False, "Account is inactive", None, None, None
    
    # Create JWT token with user info
    token_data = {
        "email": email,
        "role": role,
        "employeeId": employee_id,
        "name": name,
        "sub": email,  # Subject (standard JWT claim)
    }
    
    access_token = create_access_token(data=token_data)
    
    # Return user data without password
    user_data = {
        "email": email,
        "name": name,
        "employeeId": employee_id,
        "role": role,
        "phone": phone,
        "status": status,
    }
    
    return True, "Login successful", access_token, role, user_data
