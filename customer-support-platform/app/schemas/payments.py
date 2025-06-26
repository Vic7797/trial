from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import Field
from .base import BaseSchema, BaseCreate, BaseUpdate, BaseInDB
from uuid import UUID

class PaymentTransactionBase(BaseSchema):
    razorpay_payment_id: Optional[str] = Field(None, max_length=255)
    razorpay_order_id: Optional[str] = Field(None, max_length=255)
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="INR", max_length=3)
    status: str = Field(default="pending", max_length=20)
    plan: str = Field(..., max_length=20)
    billing_period_start: Optional[date] = None
    billing_period_end: Optional[date] = None

class PaymentTransactionCreate(PaymentTransactionBase, BaseCreate):
    organization_id: UUID
    razorpay_order_id: str  # Required during creation

class PaymentTransactionUpdate(PaymentTransactionBase, BaseUpdate):
    razorpay_payment_id: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=20)

class PaymentTransactionInDB(PaymentTransactionBase, BaseInDB):
    organization_id: UUID

class PaymentTransaction(PaymentTransactionInDB):
    pass