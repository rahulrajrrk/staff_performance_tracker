# app/dashboard/schemas.py
from typing import List, Optional
from pydantic import BaseModel, EmailStr


class EmployeeInfo(BaseModel):
    employeeId: str
    name: str
    email: EmailStr
    role: str
    designation: Optional[str] = None
    date_of_joining: Optional[str] = None  # YYYY-MM-DD or None


class CallStats(BaseModel):
    total_calls: int
    total_answered: int
    total_unanswered: int
    total_demos: int
    total_call_time_min: int
    total_demo_time_min: int
    total_time_min: int
    avg_calls_per_day: float
    avg_demos_per_day: float
    days_count: int


class PaymentStats(BaseModel):
    total_revenue: float
    total_payments_count: int
    total_new_revenue: float
    total_repeat_revenue: float
    new_payments_count: int
    repeat_payments_count: int
    new_revenue_pct: float
    repeat_revenue_pct: float


class ConversionStats(BaseModel):
    answered_rate_pct: float              # answered / total_calls * 100
    demo_to_answered_pct: float          # total_demos / total_answered * 100
    payment_to_demo_pct: float           # payment_count / total_demos * 100
    avg_call_duration_min: float         # total_call_time / total_calls
    avg_demo_duration_min: float         # total_demo_time / total_demos
    revenue_per_call: float              # total_revenue / total_calls
    revenue_per_demo: float              # total_revenue / total_demos


class IncentiveSlab(BaseModel):
    threshold_revenue: float
    rate: float  # 0.10 means 10%


class IncentiveSummary(BaseModel):
    total_revenue: float
    incentive_rate: float         # 0.10 means 10%
    incentive_rate_pct: float     # 10.0
    incentive_amount: float
    applied_slab: str
    slabs: List[IncentiveSlab]


class EmployeeDashboardResponse(BaseModel):
    success: bool
    period: str
    employee: EmployeeInfo
    calls: CallStats
    payments: PaymentStats
    conversion: ConversionStats
    incentive: IncentiveSummary
