"""Pydantic models for organization-related schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from app.core.config import settings
from uuid import UUID


class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str = Field(..., max_length=100)
    domain: Optional[str] = Field(None, max_length=100)
    plan: str = Field("free", max_length=50)
    max_agents: int = 1
    tickets_per_month: int = 100
    plan_expires_at: Optional[datetime] = None
    is_active: bool = True
    metadata_: Optional[dict] = Field(None, alias="metadata")

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class OrganizationCreate(OrganizationBase):
    """Schema for creating a new organization."""
    plan: str = "free"
    max_agents: int = settings.PLAN_LIMITS["free"]["max_agents"]
    tickets_per_month: int = settings.PLAN_LIMITS["free"]["tickets_per_month"]


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""
    name: Optional[str] = Field(None, max_length=100)
    domain: Optional[str] = Field(None, max_length=100)
    plan: Optional[str] = None
    max_agents: Optional[int] = None
    tickets_per_month: Optional[int] = None
    is_active: Optional[bool] = None
    metadata_: Optional[dict] = Field(None, alias="metadata")

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class OrganizationPlanUpdate(BaseModel):
    """Schema for updating an organization's plan."""
    plan: str

    @validator('plan')
    def validate_plan(cls, v):
        """Validate that the plan exists in PLAN_LIMITS."""
        if v not in settings.PLAN_LIMITS:
            raise ValueError(f"Invalid plan: {v}")
        return v


class OrganizationResponse(OrganizationBase):
    """Response schema for organization data."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
