# app/manager/router.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List

from google.cloud import firestore

from app.common.firestore_client import get_db_dep
from app.common.security import get_current_user
from app.payments.service import (
    create_payment_entry,
    update_payment_entry,
    get_payments,
    get_payment_by_id,
)
from app.payments.schemas import PaymentCreate, IncentiveUpdate

router = APIRouter()


def _get_employee_by_email(db: firestore.Client, email: str) -> Optional[dict]:
    """
    Helper to fetch a single user document by email. Returns a dict with
    the document data plus the Firestore document ID (key "id"). If no
    matching document exists, returns None.
    """
    users_ref = db.collection("users")
    docs = list(users_ref.where("email", "==", email).limit(1).stream())
    if not docs:
        return None
    doc = docs[0]
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return data


# ---------------------------------------------------------
# 1. GET EMPLOYEES MAPPED TO THIS MANAGER
# ---------------------------------------------------------
@router.get("/team")
def get_manager_team(
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Returns the list of employees mapped to this manager
    based on 'manager_mappings' collection.

    manager_mappings document:
    {
      "manager_email": "<manager email>",
      "employee_ids": ["SBM101", ...]   # these are employeeId values
    }
    """
    if current_user.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Not a manager")

    manager_email = current_user.get("email")
    if not manager_email:
        raise HTTPException(status_code=400, detail="Invalid manager account")

    mapping_ref = db.collection("manager_mappings").document(manager_email)
    mapping_doc = mapping_ref.get()

    if not mapping_doc.exists:
        return {"success": True, "employees": []}

    mapped_ids = mapping_doc.to_dict().get("employee_ids", []) or []

    employees = []

    # employee_ids list contains `employeeId` values.
    for emp_id in mapped_ids:
        users_ref = db.collection("users")
        q = users_ref.where("employeeId", "==", emp_id).limit(1).stream()
        emp_doc = None
        for d in q:
            emp_doc = d
            break

        if not emp_doc:
            continue

        emp_data = emp_doc.to_dict() or {}
        employees.append(
            {
                "employeeId": emp_data.get("employeeId", ""),
                "name": emp_data.get("name", ""),
                "email": emp_data.get("email", ""),
            }
        )

    return {"success": True, "employees": employees}


# ---------------------------------------------------------
# 2. MANAGER ADDS PAYMENT FOR A MAPPED EMPLOYEE
# ---------------------------------------------------------
@router.post("/payments/add")
def manager_add_payment(
    payload: PaymentCreate,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Manager adds a payment entry on behalf of a mapped employee.

    Uses PaymentCreate:
      date, employee_email, customer, customer_type, service_type,
      amount_paid, crm_link, (optional incentive override fields)
    """
    if current_user.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Not a manager")

    manager_email = current_user.get("email")
    if not manager_email:
        raise HTTPException(status_code=400, detail="Invalid manager account")

    # Check mapping
    mapping_ref = db.collection("manager_mappings").document(manager_email)
    mapping_doc = mapping_ref.get()
    if not mapping_doc.exists:
        raise HTTPException(status_code=403, detail="No employees mapped to you")

    mapped_ids = mapping_doc.to_dict().get("employee_ids", []) or []

    # Find employee by email to get employeeId
    users_ref = db.collection("users")
    q = users_ref.where("email", "==", payload.employee_email).limit(1).stream()
    emp_doc = None
    for d in q:
        emp_doc = d
        break

    if not emp_doc:
        raise HTTPException(status_code=404, detail="Employee not found")

    emp_data = emp_doc.to_dict() or {}
    emp_id = emp_data.get("employeeId")

    if not emp_id or emp_id not in mapped_ids:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to add payments for this employee",
        )

    success, msg, pay_id = create_payment_entry(
        db,
        created_by_email=manager_email,
        created_by_name=current_user.get("name", "") or "",
        payload=payload.model_dump(),
    )

    return {"success": success, "message": msg, "payment_id": pay_id}


# ---------------------------------------------------------
# 3. MANAGER LISTS PAYMENTS FOR A SELECTED EMPLOYEE
# ---------------------------------------------------------
@router.get("/payments")
def manager_list_payments(
    employeeId: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Manager views payments for an employee mapped to them,
    with optional date range filter.
    """
    if current_user.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Not a manager")

    manager_email = current_user.get("email")
    if not manager_email:
        raise HTTPException(status_code=400, detail="Invalid manager account")

    mapping_doc = db.collection("manager_mappings").document(manager_email).get()
    if (not mapping_doc.exists) or employeeId not in (
        mapping_doc.to_dict().get("employee_ids", []) or []
    ):
        raise HTTPException(status_code=403, detail="Employee not mapped to you")

    entries, total = get_payments(
        db=db,
        employee_id=employeeId,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return {
        "success": True,
        "entries": entries,
        "total": total,
        "page": page,
        "total_pages": total_pages,
    }


# ---------------------------------------------------------
# 4. MANAGER EDITS INCENTIVE FIELDS OF A PAYMENT
# ---------------------------------------------------------
@router.post("/payments/{payment_id}/edit")
def manager_edit_payment(
    payment_id: str,
    body: IncentiveUpdate,
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Manager updates incentive-related fields for a payment:
      - base_amount (optional)
      - incentive_rate_pct
      - incentive_amount
    """
    if current_user.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Not a manager")

    manager_email = current_user.get("email")
    if not manager_email:
        raise HTTPException(status_code=400, detail="Invalid manager account")

    payment = get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    employee_id = payment.get("employeeId")
    if not employee_id:
        raise HTTPException(status_code=400, detail="Payment missing employeeId")

    mapping_doc = db.collection("manager_mappings").document(manager_email).get()
    if (not mapping_doc.exists) or employee_id not in (
        mapping_doc.to_dict().get("employee_ids", []) or []
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to edit this employee's entries",
        )

    ok, msg = update_payment_entry(
        db=db,
        payment_id=payment_id,
        update_data=body.model_dump(),
    )

    return {"success": ok, "message": msg}


# ---------------------------------------------------------
# 5. MANAGER TEAM DATA: PAYMENTS & INCENTIVES
# ---------------------------------------------------------
@router.get("/team-data")
def manager_team_data(
    data_type: str = Query(
        ..., description="Type of data: 'payments' for payment entries or 'incentives' for incentive entries"
    ),
    employee_email: Optional[str] = Query(
        None, description="Filter by employee email (optional)"
    ),
    start_date: Optional[str] = Query(
        None, description="Start date (YYYY-MM-DD) to filter entries"
    ),
    end_date: Optional[str] = Query(
        None, description="End date (YYYY-MM-DD) to filter entries"
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(
        5, ge=1, le=100, description="Number of items per page (max 100)"
    ),
    current_user: dict = Depends(get_current_user),
    db: firestore.Client = Depends(get_db_dep),
):
    """
    Returns consolidated payment or incentive data for the manager's team.

    This endpoint powers the manager dashboard's Team Payments and Team Incentives
    views. It supports optional filtering by a single employee's email and a
    date range (start_date and end_date). Pagination is also supported.

    Parameters:
    - data_type: 'payments' to list payment entries, or 'incentives' to list
      incentive entries. Incentive entries are derived from payment records and
      will include only those entries with a positive incentive amount.
    - employee_email: optional email address of a team member. If supplied,
      results will be restricted to this employee. The caller must own the
      employee in their mapping; otherwise a 403 is returned.
    - start_date / end_date: optional ISO‑formatted dates to constrain the
      records. If provided, entries whose 'date' field falls outside the
      inclusive range will be filtered out. The 'date' field in the payments
      collection is stored as a YYYY‑MM‑DD string.
    - page / page_size: pagination controls. Pages are 1‑based.

    The response includes a success flag, the list of entries for the
    requested page, the total number of matching entries, the current page,
    and the total number of pages.
    """
    # Ensure only managers can access
    if current_user.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Not a manager")

    manager_email = current_user.get("email")
    if not manager_email:
        raise HTTPException(status_code=400, detail="Invalid manager account")

    # Retrieve mapping of employeeIds for this manager
    mapping_doc = db.collection("manager_mappings").document(manager_email).get()
    if not mapping_doc.exists:
        # Manager with no team returns empty list
        return {
            "success": True,
            "entries": [],
            "total": 0,
            "page": page,
            "total_pages": 1,
        }

    mapped_ids: List[str] = mapping_doc.to_dict().get("employee_ids", []) or []

    # Determine which employee IDs to query
    employee_ids: List[str] = []
    if employee_email:
        # Look up user by email
        emp_profile = _get_employee_by_email(db, employee_email)
        if not emp_profile:
            # Unknown email – treat as empty result
            return {
                "success": True,
                "entries": [],
                "total": 0,
                "page": page,
                "total_pages": 1,
            }
        emp_id = emp_profile.get("employeeId")
        if not emp_id or emp_id not in mapped_ids:
            # Not in this manager's team
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view data for this employee",
            )
        employee_ids.append(emp_id)
    else:
        # Use all mapped employees
        employee_ids = mapped_ids.copy()

    # Collect all payment documents for the selected employees
    all_entries: List[dict] = []
    for emp_id in employee_ids:
        # Build query on payments collection
        q = db.collection("payments").where("employeeId", "==", emp_id)
        # Apply date range filters if provided
        if start_date:
            q = q.where("date", ">=", start_date)
        if end_date:
            q = q.where("date", "<=", end_date)
        docs = list(q.stream())
        for doc in docs:
            data = doc.to_dict() or {}
            # Normalize fields for consistency
            entry = {
                "id": doc.id,
                "date": data.get("date"),
                "employee_name": data.get("employeeName") or data.get("employee_name"),
                "employee_email": data.get("employeeEmail"),
                "customer": data.get("customer"),
                "customer_type": data.get("customer_type"),
                "service_type": data.get("service_type"),
                "amount_paid": data.get("amount_paid"),
                "crm_link": data.get("crm_link"),
                # Incentive fields (may be absent)
                "base_amount": data.get("base_amount", 0.0),
                "incentive_rate_pct": data.get("incentive_rate_pct", 0.0),
                "incentive_amount": data.get("incentive_amount", 0.0),
            }
            all_entries.append(entry)

    # Sort entries by date (descending) then by id for stability
    all_entries.sort(key=lambda e: (e.get("date") or "", e.get("id") or ""), reverse=True)

    # Filter out non‑incentive records if requesting incentives
    if data_type.lower() == "incentives":
        all_entries = [e for e in all_entries if (e.get("incentive_amount") or 0) > 0]
    elif data_type.lower() != "payments":
        raise HTTPException(status_code=400, detail="Invalid data_type. Use 'payments' or 'incentives'")

    total_count = len(all_entries)
    total_pages = ((total_count + page_size - 1) // page_size) if total_count > 0 else 1
    # Clamp page within valid bounds
    if page > total_pages:
        page = total_pages
    if page < 1:
        page = 1
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_entries = all_entries[start_idx:end_idx]

    return {
        "success": True,
        "entries": page_entries,
        "total": total_count,
        "page": page,
        "total_pages": total_pages,
    }
