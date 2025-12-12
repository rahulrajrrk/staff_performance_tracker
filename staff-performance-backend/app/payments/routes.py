# app/payments/routes.py
from typing import Optional
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from google.cloud import firestore  # type: ignore

from app.common.firestore_client import get_db_dep
from app.common.security import (
    get_current_user,
    require_manager_or_admin,
    require_admin,
)
from app.payments.schemas import (
    PaymentCreate,
    PaymentResponse,
    PaymentListResponse,
    IncentiveEntryResponse,
    IncentiveListResponse,
)
from app.payments.service import (
    create_payment_entry,
    get_payments,
    get_incentives_for_employee,
    get_payment_by_id,
    update_payment_entry,
    delete_payment_entry,
)

router = APIRouter()


# ---------- MANAGER / ADMIN: CREATE PAYMENT ----------

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    current_user: dict = Depends(require_manager_or_admin),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Managers / Admins can create payment entries for employees.

    Frontend will:
    - Allow manager to select employee (by email)
    - Enter date, customer, type, service, amount, crm_link
    """
    created_by_email = current_user.get("email")
    created_by_name = current_user.get("name")

    ok, msg, payment_id = create_payment_entry(
        db,
        created_by_email=created_by_email,
        created_by_name=created_by_name,
        payload=payload.model_dump(),
    )

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    return {
        "success": True,
        "message": msg,
        "payment_id": payment_id,
    }


# ---------- MANAGER / ADMIN: LIST PAYMENTS ----------

@router.get("/", response_model=PaymentListResponse)
def list_payments(
    employeeId: Optional[str] = Query(
        None,
        description="Filter by employeeId (optional)",
    ),
    start_date: Optional[str] = Query(
        None, description="Start date (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None, description="End date (YYYY-MM-DD)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        5,
        ge=1,
        le=100,
        description="Items per page (5, 10, 25, 50, 100)",
    ),
    current_user: dict = Depends(require_manager_or_admin),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Managers / Admins can see all payments or filter by employeeId.

    Default behaviour in UI:
    - No date range: show last 5 (page=1, page_size=5)
    - With date range: use same pagination with filter
    """
    entries, total_count = get_payments(
        db,
        role=current_user.get("role", "Employee"),
        employee_email=employeeId,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    return PaymentListResponse(
        success=True,
        count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        entries=entries,  # Pydantic will coerce to PaymentResponse
    )


# ---------- EMPLOYEE: MY PAYMENTS (READ-ONLY) ----------

@router.get("/my", response_model=PaymentListResponse)
def list_my_payments(
    start_date: Optional[str] = Query(
        None, description="Start date (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None, description="End date (YYYY-MM-DD)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        5,
        ge=1,
        le=100,
        description="Items per page (5, 10, 25, 50, 100)",
    ),
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Employee view:
    - Read-only list of payments credited to them
    - Same date range + pagination behaviour
    """
    employee_email = current_user.get("email")
    if not employee_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee email not found in token",
        )

    entries, total_count = get_payments(
        db,
        role=current_user.get("role", "Employee"),
        employee_email=employee_email,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    return PaymentListResponse(
        success=True,
        count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        entries=entries,
    )

@router.get("/my-incentives", response_model=IncentiveListResponse)
def my_incentives(
    start_date: Optional[str] = Query(
        None,
        description="Start date (YYYY-MM-DD) for incentive range. Default: current month start",
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date (YYYY-MM-DD) for incentive range. Default: today",
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(
        5,
        ge=1,
        le=100,
        description="Entries per page (5 or 25 typically)",
    ),
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Incentive tab for employee:
    - Shows current-month total incentive (top)
    - Shows total incentive for selected date range
    - Lists incentive entries (latest first), paginated.
    """
    employee_id = current_user.get("employeeId")
    if not employee_id:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee ID missing in token",
        )

    page_entries, total_count, summary = get_incentives_for_employee(
        db=db,
        employee_id=employee_id,
        start_date=start_date or "",
        end_date=end_date or "",
        page=page,
        page_size=page_size,
    )

    return IncentiveListResponse(
        success=True,
        current_month_start=summary["current_month_start"],
        current_month_end=summary["current_month_end"],
        current_month_total_incentive=summary["current_month_total_incentive"],
        range_start=summary["range_start"],
        range_end=summary["range_end"],
        range_total_incentive=summary["range_total_incentive"],
        page=page,
        page_size=page_size,
        total_pages=summary["total_pages"],
        count=len(page_entries),
        entries=[
            IncentiveEntryResponse(**entry) for entry in page_entries
        ],
    )



# ---------- MANAGER / ADMIN: GET / UPDATE / DELETE SINGLE PAYMENT ----------

@router.get("/{payment_id}", response_model=dict)
def get_payment(
    payment_id: str,
    current_user: dict = Depends(require_manager_or_admin),
    db: firestore.Client = Depends(get_db_dep),
):
    payment = get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment entry not found",
        )

    return {"success": True, "entry": payment}


class PaymentUpdatePayload(PaymentCreate):
    """
    Reuse fields from PaymentCreate for update, but make all optional on route.
    We will unwrap with exclude_unset=True.
    """
    pass


@router.put("/{payment_id}", response_model=dict)
def update_payment(
    payment_id: str,
    payload: PaymentUpdatePayload,
    current_user: dict = Depends(require_manager_or_admin),
    db: firestore.Client = Depends(get_db_dep),
):
    update_dict = payload.model_dump(exclude_unset=True)
    # date & employee_email change allowed only for managers/admins, which is ok here

    ok, msg = update_payment_entry(db, payment_id, update_dict)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    return {"success": True, "message": msg}


@router.delete("/{payment_id}", response_model=dict)
def delete_payment(
    payment_id: str,
    current_user: dict = Depends(require_admin),  # only admin can delete
    db: firestore.Client = Depends(get_db_dep),
):
    ok, msg = delete_payment_entry(db, payment_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    return {"success": True, "message": msg}
