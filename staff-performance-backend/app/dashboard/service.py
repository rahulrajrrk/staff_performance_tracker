# app/dashboard/service.py
from datetime import date
from typing import Dict, Optional, Tuple, List

from google.cloud import firestore  # type: ignore

from app.calls.service import get_call_statistics
from app.payments.service import get_payments


# Incentive slabs: (threshold_revenue, rate)
INCENTIVE_SLABS: List[Tuple[float, float]] = [
    (200000.0, 0.20),  # >= 2L → 20%
    (100000.0, 0.15),  # >= 1L → 15%
    (50000.0, 0.10),   # >= 50k → 10%
]


def _default_month_range() -> Tuple[str, str]:
    """
    Default period: current month (1st to today).
    """
    today = date.today()
    start = today.replace(day=1)
    return start.isoformat(), today.isoformat()


def _calculate_incentive(total_revenue: float) -> Tuple[float, float, str]:
    """
    Given total revenue, return:
    - incentive_rate (0.1 means 10%)
    - incentive_amount
    - human-readable slab description
    """
    sorted_slabs = sorted(INCENTIVE_SLABS, key=lambda x: x[0], reverse=True)

    for threshold, rate in sorted_slabs:
        if total_revenue >= threshold:
            amount = round(total_revenue * rate, 2)
            label = f"{int(rate * 100)}% on revenue >= {threshold}"
            return rate, amount, label

    return 0.0, 0.0, "No incentive slab reached"


def get_employee_dashboard_data(
    db: firestore.Client,
    employee_id: str,
    employee_email: str,
    employee_name: str,
    employee_role: str,
    designation: Optional[str],
    date_of_joining: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
) -> Dict:
    """
    Aggregates:
    - Call stats from 'calls'
    - Payment stats from 'payments'
    - Conversion ratios
    - Incentive summary
    for a given employee over a date range.

    If start_date / end_date are None → current month.
    """
    # ---- Period handling ----
    if not start_date or not end_date:
        default_start, default_end = _default_month_range()
        if not start_date:
            start_date = default_start
        if not end_date:
            end_date = default_end

    period_str = f"{start_date} to {end_date}"

    # ---- Call statistics ----
    call_stats = get_call_statistics(db, employee_id, start_date, end_date)
    total_calls = call_stats["total_calls"]
    total_answered = call_stats["total_answered"]
    total_unanswered = call_stats["total_unanswered"]
    total_demos = call_stats["total_demos"]
    total_call_time_min = call_stats["total_call_time_min"]
    total_demo_time_min = call_stats["total_demo_time_min"]
    total_time_min = call_stats["total_time_min"]
    avg_calls_per_day = call_stats["avg_calls_per_day"]
    avg_demos_per_day = call_stats["avg_demos_per_day"]
    days_count = call_stats["days_count"]

    # ---- Payments / revenue stats ----
    payments, _ = get_payments(
        db,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        page=1,
        page_size=1000,  # enough for typical month
    )

    total_revenue = 0.0
    total_payments_count = len(payments)
    total_new_revenue = 0.0
    total_repeat_revenue = 0.0
    new_payments_count = 0
    repeat_payments_count = 0

    for p in payments:
        amt = float(p.get("amount_paid", 0.0))
        total_revenue += amt
        ctype = p.get("customer_type")
        if ctype == "New":
            total_new_revenue += amt
            new_payments_count += 1
        elif ctype == "Repeat":
            total_repeat_revenue += amt
            repeat_payments_count += 1

    total_revenue = round(total_revenue, 2)
    total_new_revenue = round(total_new_revenue, 2)
    total_repeat_revenue = round(total_repeat_revenue, 2)

    if total_revenue > 0:
        new_revenue_pct = round((total_new_revenue / total_revenue) * 100, 2)
        repeat_revenue_pct = round((total_repeat_revenue / total_revenue) * 100, 2)
    else:
        new_revenue_pct = 0.0
        repeat_revenue_pct = 0.0

    # ---- Conversion stats (percentages & averages) ----
    if total_calls > 0:
        answered_rate_pct = round((total_answered / total_calls) * 100, 2)
        avg_call_duration_min = round(total_call_time_min / total_calls, 2)
        revenue_per_call = round(total_revenue / total_calls, 2)
    else:
        answered_rate_pct = 0.0
        avg_call_duration_min = 0.0
        revenue_per_call = 0.0

    if total_answered > 0:
        demo_to_answered_pct = round((total_demos / total_answered) * 100, 2)
    else:
        demo_to_answered_pct = 0.0

    if total_demos > 0:
        payment_to_demo_pct = round((total_payments_count / total_demos) * 100, 2)
        avg_demo_duration_min = round(total_demo_time_min / total_demos, 2)
        revenue_per_demo = round(total_revenue / total_demos, 2)
    else:
        payment_to_demo_pct = 0.0
        avg_demo_duration_min = 0.0
        revenue_per_demo = 0.0

    # ---- Incentive calculation ----
    rate, incentive_amount, slab_label = _calculate_incentive(total_revenue)
    incentive_rate_pct = round(rate * 100, 2)

    # ---- Build response dict ----
    return {
        "period": period_str,
        "employee": {
            "employeeId": employee_id,
            "name": employee_name,
            "email": employee_email,
            "role": employee_role,
            "designation": designation,
            "date_of_joining": date_of_joining,
        },
        "calls": {
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
        },
        "payments": {
            "total_revenue": total_revenue,
            "total_payments_count": total_payments_count,
            "total_new_revenue": total_new_revenue,
            "total_repeat_revenue": total_repeat_revenue,
            "new_payments_count": new_payments_count,
            "repeat_payments_count": repeat_payments_count,
            "new_revenue_pct": new_revenue_pct,
            "repeat_revenue_pct": repeat_revenue_pct,
        },
        "conversion": {
            "answered_rate_pct": answered_rate_pct,
            "demo_to_answered_pct": demo_to_answered_pct,
            "payment_to_demo_pct": payment_to_demo_pct,
            "avg_call_duration_min": avg_call_duration_min,
            "avg_demo_duration_min": avg_demo_duration_min,
            "revenue_per_call": revenue_per_call,
            "revenue_per_demo": revenue_per_demo,
        },
        "incentive": {
            "total_revenue": total_revenue,
            "incentive_rate": rate,
            "incentive_rate_pct": incentive_rate_pct,
            "incentive_amount": incentive_amount,
            "applied_slab": slab_label,
            "slabs": [
                {"threshold_revenue": t, "rate": r}
                for t, r in INCENTIVE_SLABS
            ],
        },
    }
