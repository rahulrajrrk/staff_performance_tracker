from fastapi import APIRouter, Depends, HTTPException, status, Query
from google.cloud import firestore
from typing import Optional

from app.employees.schemas import EmployeeCreate, EmployeeResponse
from app.employees.service import (
    create_employee, get_all_employees, get_employee_by_id,
    update_employee, delete_employee, reset_employee_password
)
from app.common.firestore_client import get_db_dep
from app.common.security import get_current_user

router = APIRouter()

def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def require_manager_or_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Manager or admin access required")
    return current_user

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_new_employee(
    employee: EmployeeCreate,
    current_user: dict = Depends(require_admin),  # Only admins can create new employees
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Create a new employee document.

    This endpoint is restricted to admin users only. Managers and regular employees
    are not allowed to create new staff accounts. The caller must be authenticated
    and possess the `admin` role. The function will hash the password and enforce
    uniqueness of both the email and employeeId fields.

    Returns a JSON object containing a success flag, a human‑readable message and
    the newly created document ID.
    """
    employee_dict = employee.model_dump()
    success, message, doc_id = create_employee(db, employee_dict)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message, "employee_id": doc_id}

@router.get("/")
def list_employees(
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(require_manager_or_admin),
    db: firestore.Client = Depends(get_db_dep),
):
    employees = get_all_employees(db, role_filter=role, status_filter=status)
    return {"success": True, "count": len(employees), "employees": employees}

@router.get("/{employee_id}")
def get_employee(
    employee_id: str,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    employee = get_employee_by_id(db, employee_id)
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    user_role = current_user.get("role")
    user_email = current_user.get("email")
    
    if user_role not in ["admin", "manager"] and employee.get("email") != user_email:
        raise HTTPException(status_code=403, detail="You can only view your own profile")
    
    return {"success": True, "employee": employee}
