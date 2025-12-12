# app/payments/schemas.py
from datetime import date, datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, EmailStr, field_validator


CustomerType = Literal["New", "Repeat"]
ServiceType = Literal[
    "Voice Call",
    "RCS Registration",
    "RCS Recharge",
    "Whatsapp Registration",
    "Whatsapp Recharge",
    "SMS",
]


# ---------------------------------------------------------
# CREATE PAYMENT (Manager/Admin creates a payment entry)
# ---------------------------------------------------------
class PaymentCreate(BaseModel):
    """
    Payload used when MANAGER / ADMIN creates a payment entry.
    Includes incentive fields for override support.
    """

    date: date

    employee_email: EmailStr = Field(
        description="Email of the employee to whom this payment/ sale is credited"
    )

    customer: str = Field(min_length=1, max_length=255)
    customer_type: CustomerType
    service_type: ServiceType
    amount_paid: float = Field(gt=0, description="Amount paid by customer")
    crm_link: Optional[str] = Field(
        default=None,
        description="AntCRM link for this payment (lead / deal / invoice etc.)",
    )

    # NEW FIELDS
    base_amount: Optional[float] = Field(
        default=None,
        description="Base amount used for incentive calculation. Defaults to amount_paid if not provided.",
    )

    incentive_rate_pct: Optional[float] = Field(
        default=None,
        description="Percentage used for incentive calculation. Auto-calculated if not provided.",
    )

    incentive_amount: Optional[float] = Field(
        default=None,
        description="Direct incentive amount. Auto-calculated if not provided.",
    )

    @field_validator("crm_link")
    def strip_crm_link(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        return v or None


# ---------------------------------------------------------
# PAYMENT RESPONSE (Returned in lists)
# ---------------------------------------------------------
class PaymentResponse(BaseModel):
    """
    Shape returned in lists / details for payments.
    """

    id: str

    employeeId: str
    employeeName: str
    employeeEmail: EmailStr

    date: str  # ISO YYYY-MM-DD
    customer: str
    customer_type: CustomerType
    service_type: ServiceType
    amount_paid: float
    crm_link: Optional[str]

    # NEW – incentive data returned to UI
    base_amount: float
    incentive_rate_pct: float
    incentive_amount: float

    created_by_email: EmailStr
    created_by_name: str
    created_at: str
    updated_at: str

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def convert_datetime_to_str(cls, v):
        """
        Firestore may return datetime/timestamp objects.
        Convert them cleanly to ISO strings.
        """
        if isinstance(v, datetime):
            return v.isoformat()
        if v is None:
            return ""
        return str(v)


# ---------------------------------------------------------
# PAGINATION WRAPPER
# ---------------------------------------------------------
class PaymentListResponse(BaseModel):
    success: bool
    count: int
    page: int
    page_size: int
    total_pages: int
    entries: List[PaymentResponse]


# ---------------------------------------------------------
# INCENTIVE ENTRY FOR EACH PAYMENT
# ---------------------------------------------------------
class IncentiveEntryResponse(BaseModel):
    """
    One incentive line corresponding to a single payment entry.
    """

    payment_id: str

    date: str  # YYYY-MM-DD
    customer: str
    customer_type: CustomerType
    service_type: ServiceType
    amount_paid: float

    # NEW - full incentive details
    base_amount: float
    incentive_rate_pct: float
    incentive_amount: float


# ---------------------------------------------------------
# INCENTIVE LIST RESPONSE (EMPLOYEE VIEW)
# ---------------------------------------------------------
class IncentiveListResponse(BaseModel):
    """
    Incentives list for the employee, with top-level summary.
    """

    success: bool

    # Monthly summary
    current_month_start: str
    current_month_end: str
    current_month_total_incentive: float

    # Filter range summary
    range_start: str
    range_end: str
    range_total_incentive: float

    # Pagination details
    page: int
    page_size: int
    total_pages: int
    count: int

    entries: List[IncentiveEntryResponse]


# ---------------------------------------------------------
# MANAGER UPDATE INCENTIVE PAYLOAD
# ---------------------------------------------------------
class IncentiveUpdate(BaseModel):
    """
    Payload that manager uses to update incentives for a payment.
    """

    base_amount: Optional[float] = None
    incentive_rate_pct: float
    incentive_amount: float
