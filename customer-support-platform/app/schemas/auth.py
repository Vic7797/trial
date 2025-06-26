"""Authentication schemas."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    """Schema for user signup with organization details."""
    # User Details
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    
    # Organization Details
    organization_name: str = Field(..., max_length=255)
    organization_sector: Optional[str] = Field(None, max_length=100)
    employee_count: Optional[int] = Field(None, gt=0)


class LoginRequest(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int