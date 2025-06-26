from typing import Optional
from pydantic import Field, EmailStr
from .base import BaseSchema, BaseCreate, BaseUpdate, BaseInDB
from uuid import UUID

class CustomerBase(BaseSchema):
    email: EmailStr
    name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    channel: str = Field(..., max_length=20)
    channel_identifier: str = Field(..., max_length=255)

class CustomerCreate(CustomerBase, BaseCreate):
    organization_id: UUID

class CustomerUpdate(CustomerBase, BaseUpdate):
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    channel: Optional[str] = Field(None, max_length=20)
    channel_identifier: Optional[str] = Field(None, max_length=255)

class CustomerInDB(CustomerBase, BaseInDB):
    organization_id: UUID

class Customer(CustomerInDB):
    pass