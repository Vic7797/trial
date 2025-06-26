from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    employee_count: Mapped[Optional[int]] = mapped_column(Integer)
    plan: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="free",
        server_default="free"
    )
    monthly_ticket_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        server_default="50"
    )
    agent_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default="3"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )

    # Relationships
    users = relationship("User", back_populates="organization")
    categories = relationship("Category", back_populates="organization")
    documents = relationship("Document", back_populates="organization")
    customers = relationship("Customer", back_populates="organization")
    tickets = relationship("Ticket", back_populates="organization")


class User(Base, TimestampMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False
    )
    keycloak_user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active"
    )
    last_assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_ticket_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )

    # Relationships
    organization = relationship("Organization", back_populates="users")
    assigned_tickets = relationship("Ticket", back_populates="assigned_agent")
    category_assignments = relationship(
        "UserCategoryAssignment",
        back_populates="user"
    )