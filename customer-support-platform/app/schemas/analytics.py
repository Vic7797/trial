from datetime import date, datetime
from typing import Optional, Dict
from pydantic import Field
from .base import BaseSchema, BaseCreate, BaseUpdate, BaseInDB
from uuid import UUID


class TicketAnalyticsBase(BaseSchema):
    organization_id: UUID
    date: date
    total_tickets: int = 0
    open_tickets: int = 0
    closed_tickets: int = 0
    avg_resolution_time: Optional[float] = None
    avg_response_time: Optional[float] = None
    category_metrics: Dict[str, int] = Field(default_factory=dict)
    agent_metrics: Dict[str, int] = Field(default_factory=dict)
    channel_metrics: Dict[str, int] = Field(default_factory=dict)



class TicketAnalyticsCreate(TicketAnalyticsBase, BaseCreate):
    pass


class TicketAnalyticsUpdate(TicketAnalyticsBase, BaseUpdate):
    pass


class TicketAnalyticsInDB(TicketAnalyticsBase, BaseInDB):
    class Config:
        orm_mode = True


class TicketAnalytics(TicketAnalyticsBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True