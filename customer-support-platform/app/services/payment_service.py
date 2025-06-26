from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import razorpay

from app.config import settings
from app.core.redis import Cache
from app.crud.payments import payment as payment_crud
from app.schemas.payments import PaymentCreate, PaymentUpdate
from app.services.notification_service import (
    NotificationService,
    NotificationType
)


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        self.notification_service = NotificationService(db)
        self.cache_prefix = "payment:"

    async def create_order(
        self,
        amount: int,
        currency: str,
        organization_id: UUID,
        plan: str
    ) -> Dict[str, Any]:
        """Create a new payment order."""
        try:
            order_data = {
                "amount": amount * 100,
                "currency": currency,
                "notes": {
                    "organization_id": str(organization_id),
                    "plan": plan
                }
            }
            
            order = self.client.order.create(data=order_data)

            # Create payment record
            payment = await payment_crud.create(
                self.db,
                obj_in=PaymentCreate(
                    order_id=order["id"],
                    organization_id=organization_id,
                    amount=amount,
                    currency=currency,
                    plan=plan,
                    status="created"
                )
            )

            return {
                "payment_id": payment.id,
                "order_id": order["id"],
                "amount": amount,
                "currency": currency,
                "key_id": settings.RAZORPAY_KEY_ID
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order creation failed: {str(e)}"
            )

    async def verify_payment(
        self,
        payment_id: str,
        order_id: str,
        signature: str
    ) -> bool:
        """Verify payment signature and update status."""
        try:
            # Verify signature
            params_dict = {
                "razorpay_payment_id": payment_id,
                "razorpay_order_id": order_id,
                "razorpay_signature": signature
            }
            self.client.utility.verify_payment_signature(params_dict)

            # Get payment details
            payment_details = await payment_crud.get_by_order_id(
                self.db,
                order_id=order_id
            )
            if not payment_details:
                raise ValueError("Payment not found")

            # Update payment status
            await payment_crud.update(
                self.db,
                db_obj=payment_details,
                obj_in=PaymentUpdate(
                    status="completed",
                    payment_id=payment_id,
                    completed_at=datetime.utcnow()
                )
            )

            # Update organization plan
            await self._update_organization_plan(
                payment_details.organization_id,
                payment_details.plan
            )

            # Send notification
            await self.notification_service.send_notification(
                NotificationType.PAYMENT_RECEIVED,
                payment_details.organization_id,
                {
                    "amount": payment_details.amount,
                    "plan": payment_details.plan,
                    "valid_until": (
                        datetime.utcnow() + timedelta(days=30)
                    ).strftime("%Y-%m-%d")
                }
            )

            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment verification failed: {str(e)}"
            )

    async def _update_organization_plan(
        self,
        organization_id: UUID,
        plan: str
    ) -> None:
        """Update organization's plan details."""
        try:
            from app.crud.organizations import organization as org_crud
            
            # Get plan details
            plan_details = settings.PLAN_LIMITS[plan]
            
            # Update organization
            await org_crud.update_plan(
                self.db,
                organization_id=organization_id,
                plan=plan,
                plan_expires_at=datetime.utcnow() + timedelta(days=30),
                max_agents=plan_details["max_agents"],
                tickets_per_month=plan_details["tickets_per_month"]
            )

            # Invalidate organization cache
            await Cache.delete(f"organization:{organization_id}")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plan update failed: {str(e)}"
            )

    async def get_payment_history(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get organization's payment history."""
        try:
            cache_key = (
                f"{self.cache_prefix}history:"
                f"{organization_id}:{skip}:{limit}"
            )

            # Try cache first
            cached_history = await Cache.get(cache_key)
            if cached_history:
                return cached_history

            # Cache miss, get from database
            payments = await payment_crud.get_organization_payments(
                self.db,
                organization_id=organization_id,
                skip=skip,
                limit=limit
            )

            # Transform and cache
            history = [
                {
                    "id": str(p.id),
                    "amount": p.amount,
                    "currency": p.currency,
                    "plan": p.plan,
                    "status": p.status,
                    "created_at": p.created_at.isoformat(),
                    "completed_at": (
                        p.completed_at.isoformat()
                        if p.completed_at else None
                    )
                }
                for p in payments
            ]

            await Cache.set(cache_key, history, expire=300)  # Cache for 5 mins
            return history
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get payment history: {str(e)}"
            )