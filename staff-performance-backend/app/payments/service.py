# app/payments/service.py

from datetime import datetime, date
from typing import Dict, Optional, Tuple, List
from math import ceil

from google.cloud import firestore  # type: ignore


# ================================================================
# INTERNAL UTILITIES
# ================================================================
def _find_employee_by_email(
    db: firestore.Client,
    email: str,
) -> Optional[dict]:
    """
    Find user in 'users' collection by email.
    Store employeeId, name, email.
    """
    q = db.collection("users").where("email", "==", email).limit(1).stream()
    user_doc = None
    for d in q:
        user_doc = d
        break

    if not user_doc:
        return None

    data = user_doc.to_dict() or {}
    data["id"] = user_doc.id
    return data


# ================================================================
# INCENTIVE CALCULATOR (Default rules)
# ================================================================
INCENTIVE_SERVICES_PERCENTAGE = {"Voice Call", "RCS Recharge", "SMS"}
FIXED_INCENTIVE_WHATSAPP_REG = 250.0
FIXED_INCENTIVE_RCS_REG = 500.0


def auto_incentive_rules(payment: Dict) -> Dict:
    """
    Default incentive logic.
    Used only if the API user does NOT send incentive override.
    """

    service_type = payment.get("service_type")
    customer_type = payment.get("customer_type")
    amount_paid = float(payment.get("amount_paid", 0))

    base_amount = 0.0
    incentive_rate_pct = 0.0
    incentive_amount = 0.0

    # Rules:
    if service_type in INCENTIVE_SERVICES_PERCENTAGE and amount_paid > 0:
        base_amount = amount_paid * 0.5
        if customer_type == "New":
            incentive_rate_pct = 10.0
        else:
            incentive_rate_pct = 15.0

        incentive_amount = base_amount * (incentive_rate_pct / 100)

    elif service_type == "Whatsapp Registration":
        base_amount = 0.0
        incentive_rate_pct = 0.0
        incentive_amount = FIXED_INCENTIVE_WHATSAPP_REG

    elif service_type == "RCS Registration":
        base_amount = 0.0
        incentive_rate_pct = 0.0
        incentive_amount = FIXED_INCENTIVE_RCS_REG

    # Round to logical values
    if incentive_amount > 0:
        incentive_amount = round(incentive_amount / 10) * 10

    return {
        "base_amount": round(base_amount, 2),
        "incentive_rate_pct": incentive_rate_pct,
        "incentive_amount": round(incentive_amount, 2),
    }


# ================================================================
# CREATE PAYMENT
# ================================================================
def create_payment_entry(
    db: firestore.Client,
    created_by_email: str,
    created_by_name: str,
    payload: dict,
) -> Tuple[bool, str, Optional[str]]:
    """
    Create payment record with incentive fields stored in Firestore.

    Supports:
    ✔ Auto incentive rules
    ✔ Manager override (base_amount, rate, amount)
    """

    employee_email = payload["employee_email"]
    employee = _find_employee_by_email(db, employee_email)

    if not employee:
        return False, f"Employee with email {employee_email} not found", None

    employee_id = employee.get("employeeId", "")
    employee_name = employee.get("name", "")

    # Normalize date
    entry_date = payload["date"]
    if isinstance(entry_date, date):
        entry_date = entry_date.isoformat()

    # Manager override or auto-calc
    if (
        payload.get("base_amount") is not None
        and payload.get("incentive_rate_pct") is not None
        and payload.get("incentive_amount") is not None
    ):
        # Manager provided all fields
        base_amount = float(payload["base_amount"])
        rate_pct = float(payload["incentive_rate_pct"])
        incentive_amount = float(payload["incentive_amount"])
    else:
        # Auto incentive calculation
        inc = auto_incentive_rules(payload)
        base_amount = inc["base_amount"]
        rate_pct = inc["incentive_rate_pct"]
        incentive_amount = inc["incentive_amount"]

    now = datetime.utcnow().isoformat()

    doc = {
        "employeeId": employee_id,
        "employeeName": employee_name,
        "employeeEmail": employee_email,
        "date": entry_date,
        "customer": payload["customer"],
        "customer_type": payload["customer_type"],
        "service_type": payload["service_type"],
        "amount_paid": float(payload["amount_paid"]),
        "crm_link": payload.get("crm_link"),

        # NEW incentive fields
        "base_amount": base_amount,
        "incentive_rate_pct": rate_pct,
        "incentive_amount": incentive_amount,

        "created_by_email": created_by_email,
        "created_by_name": created_by_name,
        "created_at": now,
        "updated_at": now,
    }

    ref = db.collection("payments").document()
    ref.set(doc)

    return True, "Payment entry created successfully", ref.id


# ================================================================
# LIST PAYMENTS
# ================================================================
def get_payments(
    db: firestore.Client,
    role: str,
    employee_email: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 5,
) -> Tuple[List[dict], int]:
    """
    List payments with pagination.
    """

    # Base query ordered by date. This is always valid.
    q = db.collection("payments").order_by("date", direction=firestore.Query.DESCENDING)

    # IMPORTANT: To avoid invalid queries, we apply only ONE of the filters
    # at the database level and do the rest of the filtering in Python.
    # We prioritize the employee filter at the DB level if it exists.
    if role != "Admin":
        # For non-admins, always filter by their email.
        # This is a security measure to prevent them from seeing others' data.
        if not employee_email:
            # If no email is provided for an employee, return no results.
            return [], 0
        q = q.where("employeeEmail", "==", employee_email)
    else:  # Admin role
        if employee_email:
            q = q.where("employeeEmail", "==", employee_email)
        elif start_date or end_date:
            if start_date:
                q = q.where("date", ">=", start_date)
            if end_date:
                q = q.where("date", "<=", end_date)

    # Fetch all documents matching the primary filter.
    all_docs = list(q.stream())
    total = len(all_docs)

    offset = (page - 1) * page_size
    sliced = all_docs[offset:offset + page_size]

    entries = []
    for d in sliced:
        data = d.to_dict() or {}
        data["id"] = d.id

        # ensure incentive fields exist
        data.setdefault("base_amount", 0.0)
        data.setdefault("incentive_rate_pct", 0.0)
        data.setdefault("incentive_amount", 0.0)
        entries.append(data)

    return entries, total


# ================================================================
# GET PAYMENT BY ID
# ================================================================
def get_payment_by_id(
    db: firestore.Client, payment_id: str
) -> Optional[dict]:

    d = db.collection("payments").document(payment_id).get()
    if not d.exists:
        return None

    data = d.to_dict() or {}
    data["id"] = d.id

    # ensure fields
    data.setdefault("base_amount", 0.0)
    data.setdefault("incentive_rate_pct", 0.0)
    data.setdefault("incentive_amount", 0.0)

    return data


# ================================================================
# MANAGER INCENTIVE UPDATE
# ================================================================
def update_payment_entry(
    db: firestore.Client,
    payment_id: str,
    update_data: dict,
) -> Tuple[bool, str]:
    """
    Manager/Admin updating incentive fields.
    """

    ref = db.collection("payments").document(payment_id)
    doc = ref.get()

    if not doc.exists:
        return False, "Payment entry not found"

    # sanitize
    update_data = {k: v for k, v in update_data.items() if v is not None}
    if not update_data:
        return False, "No update data provided"

    update_data["updated_at"] = datetime.utcnow().isoformat()
    ref.update(update_data)

    return True, "Payment entry updated"


# ================================================================
# DELETE PAYMENT
# ================================================================
def delete_payment_entry(
    db: firestore.Client,
    payment_id: str,
) -> Tuple[bool, str]:

    ref = db.collection("payments").document(payment_id)
    doc = ref.get()

    if not doc.exists:
        return False, "Payment entry not found"

    ref.delete()
    return True, "Payment entry deleted"


# ================================================================
# EMPLOYEE INCENTIVE SUMMARY
# ================================================================
def get_incentives_for_employee(
    db: firestore.Client,
    employee_id: str,
    start_date: str,
    end_date: str,
    page: int,
    page_size: int,
) -> Tuple[List[Dict], int, Dict]:

    today = date.today()
    current_month_start = today.replace(day=1).isoformat()
    current_month_end = today.isoformat()

    if not start_date:
        start_date = current_month_start
    if not end_date:
        end_date = current_month_end

    # Base query for the employee
    q = db.collection("payments").where("employeeId", "==", employee_id)

    # Fetch all entries for summary calculations
    all_docs = list(q.stream())
    all_entries = []
    current_month_total = 0.0

    for d in all_docs:
        data = d.to_dict() or {}
        pay_date = data.get("date")
        if not pay_date:
            continue

        base = float(data.get("base_amount", 0))
        incentive = float(data.get("incentive_amount", 0))
        rate = float(data.get("incentive_rate_pct", 0))

        # skip 0 incentive
        if incentive <= 0:
            continue

        entry = {
            "payment_id": d.id,
            "date": pay_date,
            "customer": data.get("customer", ""),
            "customer_type": data.get("customer_type", ""),
            "service_type": data.get("service_type", ""),
            "amount_paid": float(data.get("amount_paid", 0)),
            "base_amount": base,
            "incentive_rate_pct": rate,
            "incentive_amount": incentive,
        }

        all_entries.append(entry)

        # current month
        if current_month_start <= pay_date <= current_month_end:
            current_month_total += incentive

    # Filter entries for the selected date range for pagination
    filtered = [
        e for e in all_entries
        if start_date <= e["date"] <= end_date
    ]

    # Calculate total incentive for the filtered range
    range_total = sum(e["incentive_amount"] for e in filtered)

    # Sort the filtered results for stable pagination
    filtered.sort(key=lambda e: (e["date"], e["payment_id"]), reverse=True)

    total_count = len(filtered)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_entries = filtered[start_idx:end_idx]

    total_pages = ceil(total_count / page_size) if total_count else 1

    summary = {
        "current_month_start": current_month_start,
        "current_month_end": current_month_end,
        "current_month_total_incentive": round(current_month_total, 2),
        "range_start": start_date,
        "range_end": end_date,
        "range_total_incentive": round(range_total, 2),
        "total_pages": total_pages,
    }

    return page_entries, total_count, summary
