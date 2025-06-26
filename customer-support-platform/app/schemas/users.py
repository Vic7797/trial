from typing import Optional
from pydantic import EmailStr, Field, validator
from .base import BaseSchema, BaseCreate, BaseUpdate, BaseInDB
from uuid import UUID
from datetime import datetime

class UserBase(BaseSchema):
    email: EmailStr
    name: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    role: str = Field(..., max_length=20)
    status: str = Field(default="active", max_length=20)
    is_active: bool = Field(default=True)
    last_assigned_at: Optional[datetime] = None
    current_ticket_count: int = 0

class UserCreate(UserBase, BaseCreate):
    organization_id: UUID
    keycloak_user_id: Optional[str] = None

class UserUpdate(UserBase, BaseUpdate):
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None

class UserInDB(UserBase, BaseInDB):
    organization_id: UUID
    keycloak_user_id: Optional[str] = None
    last_assigned_at: Optional[datetime] = None
    current_ticket_count: int = 0

class User(UserInDB):
    pass