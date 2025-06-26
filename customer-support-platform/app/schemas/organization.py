from typing import Optional
from pydantic import Field
from .base import BaseSchema, BaseCreate, BaseUpdate, BaseInDB

class OrganizationBase(BaseSchema):
    name: str = Field(..., max_length=255)
    sector: Optional[str] = Field(None, max_length=100)
    employee_count: Optional[int] = None
    plan: str = Field(default="free", max_length=20)
    monthly_ticket_limit: int = Field(default=50, ge=0)
    agent_limit: int = Field(default=3, ge=1)
    is_active: bool = Field(default=True)

class OrganizationCreate(OrganizationBase, BaseCreate):
    pass

class OrganizationUpdate(OrganizationBase, BaseUpdate):
    name: Optional[str] = Field(None, max_length=255)
    plan: Optional[str] = Field(None, max_length=20)
    monthly_ticket_limit: Optional[int] = Field(None, ge=0)
    agent_limit: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None

class OrganizationInDB(OrganizationBase, BaseInDB):
    pass

class Organization(OrganizationInDB):
    pass