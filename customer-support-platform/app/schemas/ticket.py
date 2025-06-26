from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, BaseCreate, BaseUpdate, BaseInDB


class TicketBase(BaseSchema):
    subject: str = Field(..., max_length=255)
    description: str
    channel: str = Field(..., max_length=20)
    category_id: Optional[UUID] = None
    assigned_agent_id: Optional[UUID] = None
    criticality: str = Field(default="low", max_length=20)
    status: str = Field(default="open", max_length=20)


class TicketCreate(TicketBase, BaseCreate):
    organization_id: UUID
    customer_id: UUID


class TicketUpdate(TicketBase, BaseUpdate):
    subject: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    channel: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field(None, max_length=20)


class TicketInDB(TicketBase, BaseInDB):
    organization_id: UUID
    customer_id: UUID
    ai_confidence_score: Optional[Decimal] = None
    assigned_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class Ticket(TicketInDB):
    pass