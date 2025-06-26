from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class PaymentTransaction(Base, TimestampMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False
    )
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True
    )
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
        server_default="INR"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending"
    )
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    billing_period_start: Mapped[Optional[date]] = mapped_column(Date)
    billing_period_end: Mapped[Optional[date]] = mapped_column(Date)

    # Relationships
    organization = relationship("Organization")