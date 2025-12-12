# app/dashboard/routes.py
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from google.cloud import firestore  # type: ignore

from app.common.firestore_client import get_db_dep
from app.common.security import (
    get_current_user,
    require_manager_or_admin,
)
from app.dashboard.schemas import EmployeeDashboardResponse
from app.dashboard.service import get_employee_dashboard_data

router = APIRouter()


def _get_employee_profile_by_email(db: firestore.Client, email: str) -> Optional[dict]:
    users_ref = db.collection("users")
    docs = list(users_ref.where("email", "==", email).limit(1).stream())
    if not docs:
        return None
    d = docs[0]
    data = d.to_dict() or {}
    data["id"] = d.id
    return data


def _get_employee_profile_by_employeeId(db: firestore.Client, employeeId: str) -> Optional[dict]:
    users_ref = db.collection("users")
    docs = list(users_ref.where("employeeId", "==", employeeId).limit(1).stream())
    if not docs:
        return None
    d = docs[0]
    data = d.to_dict() or {}
    data["id"] = d.id
    return data


@router.get("/my", response_model=EmployeeDashboardResponse)
def my_dashboard(
    start_date: Optional[str] = Query(
        None, description="Start date (YYYY-MM-DD). Default: start of current month"
    ),
    end_date: Optional[str] = Query(
        None, description="End date (YYYY-MM-DD). Default: today"
    ),
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Employee dashboard:
    - Called right after login for the logged-in employee.
    - Shows name, role, (optional) designation & DOJ, and current-month stats.
    """
    employee_id = current_user.get("employeeId")
    employee_email = current_user.get("email")
    employee_name = current_user.get("name")
    employee_role = current_user.get("role")

    if not employee_id or not employee_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee information missing in token",
        )

    profile = _get_employee_profile_by_email(db, employee_email) or {}
    designation = profile.get("designation")
    date_of_joining = profile.get("date_of_joining")

    data = get_employee_dashboard_data(
        db=db,
        employee_id=employee_id,
        employee_email=employee_email,
        employee_name=employee_name,
        employee_role=employee_role,
        designation=designation,
        date_of_joining=date_of_joining,
        start_date=start_date,
        end_date=end_date,
    )

    return EmployeeDashboardResponse(success=True, **data)


@router.get("/employee", response_model=EmployeeDashboardResponse)
def employee_dashboard(
    employeeId: str = Query(..., description="EmployeeId of the staff (e.g., SBM101)"),
    start_date: Optional[str] = Query(
        None, description="Start date (YYYY-MM-DD). Default: start of current month"
    ),
    end_date: Optional[str] = Query(
        None, description="End date (YYYY-MM-DD). Default: today"
    ),
    current_user: dict = Depends(require_manager_or_admin),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Manager/Admin view:
    - Dashboard for a specific employeeId
    - Same stats as /dashboard/my, but for any staff member.
    """
    profile = _get_employee_profile_by_employeeId(db, employeeId)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    employee_email = profile.get("email")
    employee_name = profile.get("name", employeeId)
    employee_role = profile.get("role", "employee")
    designation = profile.get("designation")
    date_of_joining = profile.get("date_of_joining")

    data = get_employee_dashboard_data(
        db=db,
        employee_id=employeeId,
        employee_email=employee_email,
        employee_name=employee_name,
        employee_role=employee_role,
        designation=designation,
        date_of_joining=date_of_joining,
        start_date=start_date,
        end_date=end_date,
    )

    return EmployeeDashboardResponse(success=True, **data)
