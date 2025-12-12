# app/calls/service.py
from google.cloud import firestore
from datetime import datetime, date, timedelta
from typing import Optional, Tuple, List, Dict
import math


def create_call_entry(
    db: firestore.Client,
    employee_id: str,
    employee_name: str,
    employee_email: str,
    entry_data: dict
) -> Tuple[bool, str, Optional[str]]:
    """Create a new call entry for an employee (one per employee per date)."""
    calls_ref = db.collection("calls")

    # Normalise date to ISO string
    entry_date = entry_data.get("date")
    if isinstance(entry_date, date):
        entry_date_str = entry_date.isoformat()
    elif isinstance(entry_date, str):
        entry_date_str = entry_date
    else:
        return False, "Invalid or missing date", None

    # Check if entry already exists for this employee & date
    existing_q = (
        calls_ref
        .where("employeeId", "==", employee_id)
        .where("date", "==", entry_date_str)
        .limit(1)
    )
    existing_docs = list(existing_q.stream())

    if existing_docs:
        return False, f"Entry already exists for {entry_date_str}. Please contact your manager to update.", None

    # Safely extract fields from entry_data
    answered_calls = int(entry_data.get("answered_calls", 0))
    unanswered_calls = int(entry_data.get("unanswered_calls", 0))
    call_time_min = int(entry_data.get("call_time_min", 0))
    demos_conducted = int(entry_data.get("demos_conducted", 0))
    demo_time_min = int(entry_data.get("demo_time_min", 0))
    demo_cards = entry_data.get("demo_cards") or []
    google_meet_links = entry_data.get("google_meet_links") or []
    notes = entry_data.get("notes")

    total_calls = answered_calls + unanswered_calls
    total_time_min = call_time_min + demo_time_min

    now = datetime.utcnow()

    doc_data = {
        "employeeId": employee_id,
        "employeeName": employee_name,
        "employeeEmail": employee_email,
        "date": entry_date_str,
        "answered_calls": answered_calls,
        "unanswered_calls": unanswered_calls,
        "total_calls": total_calls,
        "call_time_min": call_time_min,
        "demos_conducted": demos_conducted,
        "demo_cards": demo_cards,
        "demo_time_min": demo_time_min,
        "google_meet_links": google_meet_links,
        "total_time_min": total_time_min,
        "notes": notes,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    # Create document
    doc_ref = calls_ref.document()
    doc_ref.set(doc_data)

    return True, "Call entry created successfully", doc_ref.id


def get_call_entries(
    db: firestore.Client,
    employee_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 5
) -> Tuple[List[dict], int]:
    """Get call entries with pagination and filters."""
    calls_ref = db.collection("calls")
    query = calls_ref
    
    # Apply filters
    if employee_id:
        query = query.where("employeeId", "==", employee_id)
    
    if start_date:
        query = query.where("date", ">=", start_date)
    
    if end_date:
        query = query.where("date", "<=", end_date)
    
    # Order by date descending (most recent first)
    query = query.order_by("date", direction=firestore.Query.DESCENDING)
    
    # Get all matching documents for count
    all_docs = list(query.stream())
    total_count = len(all_docs)
    
    # Apply pagination
    offset = (page - 1) * page_size
    paginated_docs = all_docs[offset:offset + page_size]
    
    # Convert to dict
    entries = []
    for doc in paginated_docs:
        data = doc.to_dict()
        if data:
            data["id"] = doc.id
            # Ensure all fields exist
            data.setdefault("created_at", "")
            data.setdefault("updated_at", "")
            data.setdefault("notes", "")
            data.setdefault("google_meet_links", [])
            entries.append(data)
    
    return entries, total_count


def get_call_entry_by_id(db: firestore.Client, entry_id: str) -> Optional[dict]:
    """Get a single call entry by ID"""
    doc_ref = db.collection("calls").document(entry_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return None
    
    data = doc.to_dict()
    if data:
        data["id"] = doc.id
        # Ensure all fields exist
        data.setdefault("created_at", "")
        data.setdefault("updated_at", "")
        data.setdefault("notes", "")
        data.setdefault("google_meet_links", [])
    
    return data


def update_call_entry(
    db: firestore.Client,
    entry_id: str,
    update_data: dict
) -> Tuple[bool, str]:
    """Update a call entry"""
    doc_ref = db.collection("calls").document(entry_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return False, "Call entry not found"
    
    # Remove None values
    update_data = {k: v for k, v in update_data.items() if v is not None}
    
    if not update_data:
        return False, "No data to update"
    
    # Recalculate totals if needed
    current_data = doc.to_dict()
    
    if "answered_calls" in update_data or "unanswered_calls" in update_data:
        answered = update_data.get("answered_calls", current_data.get("answered_calls", 0))
        unanswered = update_data.get("unanswered_calls", current_data.get("unanswered_calls", 0))
        update_data["total_calls"] = answered + unanswered
    
    if "call_time_min" in update_data or "demo_time_min" in update_data:
        call_time = update_data.get("call_time_min", current_data.get("call_time_min", 0))
        demo_time = update_data.get("demo_time_min", current_data.get("demo_time_min", 0))
        update_data["total_time_min"] = call_time + demo_time
    
    # Update timestamp
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    # Update document
    doc_ref.update(update_data)
    
    return True, "Call entry updated successfully"


def delete_call_entry(db: firestore.Client, entry_id: str) -> Tuple[bool, str]:
    """Delete a call entry"""
    doc_ref = db.collection("calls").document(entry_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return False, "Call entry not found"
    
    doc_ref.delete()
    return True, "Call entry deleted successfully"


from typing import Dict
from google.cloud import firestore  # make sure this import is at top of file


def get_call_statistics(
    db: firestore.Client,
    employee_id: str,
    start_date: str,
    end_date: str,
) -> Dict:
    """
    Compute call statistics for an employee between start_date and end_date.

    NOTE:
    - To avoid composite index issues in Firestore, we:
      * Query only by employeeId in Firestore
      * Do date filtering (start_date/end_date) in Python
    """
    calls_ref = db.collection("calls")

    # Only filter by employeeId in Firestore – this uses default single-field index.
    query = calls_ref.where("employeeId", "==", employee_id)

    docs = list(query.stream())

    total_calls = 0
    total_answered = 0
    total_unanswered = 0
    total_demos = 0
    total_call_time_min = 0
    total_demo_time_min = 0
    total_time_min = 0

    dates_seen = set()

    for doc in docs:
        data = doc.to_dict() or {}
        entry_date = data.get("date")  # stored as "YYYY-MM-DD" string

        # If we have a date range, filter entries in Python
        if start_date and entry_date and entry_date < start_date:
            continue
        if end_date and entry_date and entry_date > end_date:
            continue

        dates_seen.add(entry_date)

        answered = int(data.get("answered_calls", 0))
        unanswered = int(data.get("unanswered_calls", 0))
        total_c = int(data.get("total_calls", answered + unanswered))
        call_time = int(data.get("call_time_min", 0))
        demos = int(data.get("demos_conducted", 0))
        demo_time = int(data.get("demo_time_min", 0))
        total_time = int(data.get("total_time_min", call_time + demo_time))

        total_calls += total_c
        total_answered += answered
        total_unanswered += unanswered
        total_demos += demos
        total_call_time_min += call_time
        total_demo_time_min += demo_time
        total_time_min += total_time

    days_count = len(dates_seen) if dates_seen else 0

    if days_count > 0:
        avg_calls_per_day = round(total_calls / days_count, 2)
        avg_demos_per_day = round(total_demos / days_count, 2)
    else:
        avg_calls_per_day = 0.0
        avg_demos_per_day = 0.0

    return {
        "total_calls": total_calls,
        "total_answered": total_answered,
        "total_unanswered": total_unanswered,
        "total_demos": total_demos,
        "total_call_time_min": total_call_time_min,
        "total_demo_time_min": total_demo_time_min,
        "total_time_min": total_time_min,
        "avg_calls_per_day": avg_calls_per_day,
        "avg_demos_per_day": avg_demos_per_day,
        "days_count": days_count,
    }

