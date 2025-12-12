# app/employees/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional


class EmployeeCreate(BaseModel):
    """Schema for creating a new employee"""
    email: EmailStr
    name: str
    phone: str
    role: str  # "employee", "manager", "admin"
    employeeId: str
    password: str  # Initial password set by admin
    status: str = "active"
    target_calls: int = 0
    target_demos: int = 0
    target_revenue: float = 0.0


class EmployeeUpdate(BaseModel):
    """Schema for updating employee details"""
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    target_calls: Optional[int] = None
    target_demos: Optional[int] = None
    target_revenue: Optional[float] = None


class EmployeeResponse(BaseModel):
    """Schema for employee response (without password)"""
    id: str
    email: str
    name: str
    phone: str
    role: str
    employeeId: str
    status: str
    target_calls: int
    target_demos: int
    target_revenue: float


class EmployeeListResponse(BaseModel):
    """Schema for listing employees"""
    success: bool
    count: int
    employees: list[EmployeeResponse]
