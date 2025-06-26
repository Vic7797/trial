from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    channel_identifier: Mapped[str] = mapped_column(String(255))

    # Relationships
    organization = relationship("Organization", back_populates="customers")
    tickets = relationship("Ticket", back_populates="customer")


class Ticket(Base, TimestampMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer.id", ondelete="CASCADE"),
        nullable=False
    )
    category_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("category.id")
    )
    assigned_agent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("user.id")
    )

    # Ticket details
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)

    # AI Assessment
    criticality: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="low",
        server_default="low"
    )
    ai_confidence_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2)
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        server_default="open"
    )

    # Status timestamps
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    organization = relationship("Organization", back_populates="tickets")
    customer = relationship("Customer", back_populates="tickets")
    category = relationship("Category", back_populates="tickets")
    assigned_agent = relationship("User", back_populates="assigned_tickets")
    messages = relationship("TicketMessage", back_populates="ticket")


class TicketMessage(Base, TimestampMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True)
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("ticket.id", ondelete="CASCADE"),
        nullable=False
    )
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL")
    )
    message_content: Mapped[str] = mapped_column(String, nullable=False)
    is_internal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false"
    )

    # Relationships
    ticket = relationship("Ticket", back_populates="messages")
    sender = relationship("User")