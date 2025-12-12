# app/auth/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserData(BaseModel):
    email: str
    name: str
    employeeId: str
    role: str
    phone: str
    status: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    role: Optional[str] = None
    user: Optional[UserData] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str
