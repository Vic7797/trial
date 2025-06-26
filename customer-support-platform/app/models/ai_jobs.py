from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AICrewJob(Base):
    id: Mapped[UUID] = mapped_column(primary_key=True)
    ticket_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("ticket.id", ondelete="CASCADE")
    )
    crew_type: Mapped[str] = mapped_column(String(20), nullable=False)
    job_id: Mapped[Optional[str]] = mapped_column(String(255))
    input_data: Mapped[dict] = mapped_column(JSON)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(String)

    # Relationships
    ticket = relationship("Ticket")