# app/calls/routes.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from google.cloud import firestore
from typing import Optional
from datetime import date, timedelta
import math

from app.calls.schemas import (
    CallEntryCreate,
    CallEntryUpdate,
    CallEntryResponse,
    CallEntryListResponse,
    CallStatsResponse
)
from app.calls.service import (
    create_call_entry,
    get_call_entries,
    get_call_entry_by_id,
    update_call_entry,
    delete_call_entry,
    get_call_statistics
)
from app.common.firestore_client import get_db_dep
from app.common.security import get_current_user

router = APIRouter()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_entry(
    entry: CallEntryCreate,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Create a new call entry for the current user.
    Each employee can only create entries for themselves.
    """
    employee_id = current_user.get("employeeId")
    employee_name = current_user.get("name")
    employee_email = current_user.get("email")
    
    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee ID not found in user profile"
        )
    
    entry_dict = entry.model_dump()
    
    success, message, doc_id = create_call_entry(
        db, employee_id, employee_name, employee_email, entry_dict
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {
        "success": True,
        "message": message,
        "entry_id": doc_id
    }


@router.get("/", response_model=CallEntryListResponse)
def list_entries(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(5, ge=1, le=100, description="Items per page (5, 10, 25, 50, 100)"),
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Get call entries for the current user with pagination.
    Supports date filtering and pagination (5, 10, 25, 50, or 100 items per page).
    Results are sorted by date (most recent first).
    """
    employee_id = current_user.get("employeeId")
    
    # Managers and admins can see all entries, employees see only their own
    if current_user.get("role") not in ["admin", "manager"]:
        filter_employee_id = employee_id
    else:
        filter_employee_id = None  # Admins/managers see all
    
    entries, total_count = get_call_entries(
        db,
        employee_id=filter_employee_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )
    
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
    
    return CallEntryListResponse(
        success=True,
        count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        entries=entries
    )


@router.get("/my-entries", response_model=CallEntryListResponse)
def list_my_entries(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(5, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Get call entries for the logged-in employee only.
    Default shows last 5 entries, can be changed to 25, 50, or 100.
    """
    employee_id = current_user.get("employeeId")
    
    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee ID not found"
        )
    
    entries, total_count = get_call_entries(
        db,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )
    
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
    
    return CallEntryListResponse(
        success=True,
        count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        entries=entries
    )


@router.get("/stats", response_model=CallStatsResponse)
def get_stats(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Get call statistics for the current user over a date range.
    If no dates provided, returns stats for last 30 days.
    """
    employee_id = current_user.get("employeeId")
    employee_name = current_user.get("name")
    
    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee ID not found"
        )
    
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = date.today().isoformat()
    if not start_date:
        start = date.today() - timedelta(days=30)
        start_date = start.isoformat()
    
    stats = get_call_statistics(db, employee_id, start_date, end_date)
    
    period = f"{start_date} to {end_date}"
    
    return CallStatsResponse(
        success=True,
        employeeId=employee_id,
        employeeName=employee_name,
        period=period,
        **stats
    )


@router.get("/{entry_id}", response_model=dict)
def get_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Get a specific call entry by ID.
    Employees can only view their own entries.
    Managers and admins can view any entry.
    """
    entry = get_call_entry_by_id(db, entry_id)
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call entry not found"
        )
    
    # Check permissions
    user_role = current_user.get("role")
    user_employee_id = current_user.get("employeeId")
    
    if user_role not in ["admin", "manager"] and entry.get("employeeId") != user_employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own entries"
        )
    
    return {
        "success": True,
        "entry": entry
    }


@router.put("/{entry_id}", response_model=dict)
def update_entry(
    entry_id: str,
    entry_update: CallEntryUpdate,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Update a call entry.
    Employees can only update their own entries.
    Admins can update any entry.
    """
    # First get the entry to check ownership
    entry = get_call_entry_by_id(db, entry_id)
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call entry not found"
        )
    
    # Check permissions
    user_role = current_user.get("role")
    user_employee_id = current_user.get("employeeId")
    
    if user_role != "admin" and entry.get("employeeId") != user_employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own entries"
        )
    
    update_dict = entry_update.model_dump(exclude_unset=True)
    
    success, message = update_call_entry(db, entry_id, update_dict)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {
        "success": True,
        "message": message
    }


@router.delete("/{entry_id}", response_model=dict)
def delete_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Delete a call entry.
    Employees can only delete their own entries.
    Admins can delete any entry.
    """
    # First get the entry to check ownership
    entry = get_call_entry_by_id(db, entry_id)
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call entry not found"
        )
    
    # Check permissions
    user_role = current_user.get("role")
    user_employee_id = current_user.get("employeeId")
    
    if user_role != "admin" and entry.get("employeeId") != user_employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own entries"
        )
    
    success, message = delete_call_entry(db, entry_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {
        "success": True,
        "message": message
    }
