from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Category(Base, TimestampMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String)
    color: Mapped[str] = mapped_column(String(7))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )
    
    # Vector DB metadata fields for document and ticket matching
    keywords: Mapped[Optional[str]] = mapped_column(String(500))
    embedding_config: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Visibility and routing
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    auto_assign_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    
    # SLA Configuration
    response_sla_minutes: Mapped[int] = mapped_column(default=60)  # Default 1 hour
    resolution_sla_minutes: Mapped[int] = mapped_column(default=480)  # Default 8 hours
    priority_level: Mapped[int] = mapped_column(default=3)  # 1=Highest, 5=Lowest

    # Relationships
    organization = relationship("Organization", back_populates="categories")
    assigned_users = relationship(
        "UserCategoryAssignment",
        back_populates="category"
    )
    documents = relationship(
        "DocumentCategoryAssignment",
        back_populates="category"
    )
    tickets = relationship("Ticket", back_populates="category")


class UserCategoryAssignment(Base):
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False
    )
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("category.id", ondelete="CASCADE"),
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="category_assignments")
    category = relationship("Category", back_populates="assigned_users")
