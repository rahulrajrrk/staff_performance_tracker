from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import date, datetime


class CallEntryCreate(BaseModel):
    """Schema for creating a new call entry"""
    date: date
    answered_calls: int = Field(ge=0, description="Number of answered calls")
    unanswered_calls: int = Field(ge=0, description="Number of unanswered calls")
    call_time_min: int = Field(ge=0, description="Total call time in minutes")
    demos_conducted: int = Field(ge=0, description="Number of demos conducted")
    demo_cards: List[str] = Field(default_factory=list, description="AntCRM demo card links")
    demo_time_min: int = Field(default=0, ge=0, description="Total demo time in minutes")
    google_meet_links: List[str] = Field(default_factory=list, description="Google Meet links (optional)")
    notes: Optional[str] = Field(default=None, max_length=1000, description="Additional notes")

    @field_validator('demo_cards')
    def validate_demo_cards(cls, v, info):
        """Ensure demo_cards are provided if demos_conducted > 0"""
        demos = info.data.get('demos_conducted', 0)
        if demos > 0 and len(v) == 0:
            raise ValueError('Demo card links are required when demos_conducted > 0')
        if len(v) != demos:
            raise ValueError(f'Number of demo cards ({len(v)}) must match demos_conducted ({demos})')
        # Validate URLs
        for link in v:
            if not link.strip():
                raise ValueError('Demo card links cannot be empty')
        return v

    @field_validator('google_meet_links')
    def validate_meet_links(cls, v, info):
        """Validate google meet links count does not exceed demos"""
        demos = info.data.get('demos_conducted', 0)
        if len(v) > demos:
            raise ValueError(f'Cannot have more meet links ({len(v)}) than demos ({demos})')
        # Remove empty strings and trim
        return [link.strip() for link in v if link.strip()]

    @model_validator(mode='after')
    def validate_totals(self):
        """Validate that total_calls = answered + unanswered and is > 0"""
        total = self.answered_calls + self.unanswered_calls
        if total == 0:
            raise ValueError('Total calls must be greater than 0')
        return self

    @model_validator(mode='after')
    def validate_times(self):
        """
        Additional business rules:
        - If answered_calls > 0 => call_time_min must be > 0
        - If demos_conducted > 0 => demo_time_min must be > 0
        """
        if self.answered_calls > 0 and self.call_time_min <= 0:
            raise ValueError('Call time (in minutes) is required when there are answered calls')
        if self.demos_conducted > 0 and self.demo_time_min <= 0:
            raise ValueError('Demo time (in minutes) is required when demos are conducted')
        return self


class CallEntryUpdate(BaseModel):
    """Schema for updating a call entry"""
    answered_calls: Optional[int] = Field(None, ge=0)
    unanswered_calls: Optional[int] = Field(None, ge=0)
    call_time_min: Optional[int] = Field(None, ge=0)
    demos_conducted: Optional[int] = Field(None, ge=0)
    demo_cards: Optional[List[str]] = None
    demo_time_min: Optional[int] = Field(None, ge=0)
    google_meet_links: Optional[List[str]] = None
    notes: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode='after')
    def validate_update(self):
        """Validate update data"""
        if self.demos_conducted is not None and self.demos_conducted > 0:
            if self.demo_cards is None or len(self.demo_cards) == 0:
                raise ValueError('Demo cards required when demos_conducted > 0')
            if len(self.demo_cards) != self.demos_conducted:
                raise ValueError('Number of demo cards must match demos_conducted')
        return self


class CallEntryResponse(BaseModel):
    """Schema for call entry response"""
    id: str
    employeeId: str
    employeeName: str
    employeeEmail: str
    date: str
    answered_calls: int
    unanswered_calls: int
    total_calls: int
    call_time_min: int
    demos_conducted: int
    demo_cards: List[str]
    demo_time_min: int
    google_meet_links: List[str]
    total_time_min: int
    notes: Optional[str]
    created_at: str
    updated_at: str

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def convert_datetime_to_str(cls, v):
        """Allow Firestore timestamps or None and convert to string."""
        if isinstance(v, datetime):
            return v.isoformat()
        if v is None:
            return ""
        return str(v)


class CallEntryListResponse(BaseModel):
    """Schema for listing call entries with pagination"""
    success: bool
    count: int
    page: int
    page_size: int
    total_pages: int
    entries: List[CallEntryResponse]


class CallStatsResponse(BaseModel):
    """Schema for call statistics"""
    success: bool
    employeeId: str
    employeeName: str
    period: str
    total_calls: int
    total_answered: int
    total_unanswered: int
    total_demos: int
    total_call_time_min: int
    total_demo_time_min: int
    total_time_min: int
    avg_calls_per_day: float
    avg_demos_per_day: float
