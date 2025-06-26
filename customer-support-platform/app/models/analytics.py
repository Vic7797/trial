from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class TicketAnalytics(Base, TimestampMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    category_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("category.id")
    )
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("user.id")
    )

    # Metrics
    total_tickets: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    resolved_tickets: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    avg_resolution_time_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2)
    )
    criticality_breakdown: Mapped[dict] = mapped_column(JSON)

    # Relationships
    organization = relationship("Organization")
    category = relationship("Category")
    agent = relationship("User")