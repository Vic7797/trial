"""Razorpay integration for payment processing."""
from typing import Dict, Any, Optional
import razorpay
from fastapi import HTTPException, status

from app.config import settings

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


class RazorpayService:
    """Service for handling Razorpay payment operations."""

    @staticmethod
    async def create_order(
        amount: int,
        currency: str = "INR",
        notes: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a new payment order."""
        try:
            order_data = {
                "amount": amount * 100,
                "currency": currency,
                "notes": notes or {}
            }
            order = razorpay_client.order.create(data=order_data)
            return order
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create order: {str(e)}"
            )


    @staticmethod
    async def verify_payment(
        payment_id: str,
        order_id: str,
        signature: str
    ) -> bool:
        """Verify payment signature."""
        try:
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            razorpay_client.utility.verify_payment_signature(params_dict)
            return True
        except Exception:
            return False


    @staticmethod
    async def get_payment_details(payment_id: str) -> Dict[str, Any]:
        """Get payment details by payment ID."""
        try:
            payment = razorpay_client.payment.fetch(payment_id)
            return payment
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment not found: {str(e)}"
            )


    @staticmethod
    async def refund_payment(
        payment_id: str,
        amount: Optional[int] = None
    ) -> Dict[str, Any]:
        """Refund a payment."""
        try:
            refund_data = {"payment_id": payment_id}
            if amount:
                refund_data["amount"] = amount * 100
            refund = razorpay_client.payment.refund(payment_id, refund_data)
            return refund
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Refund failed: {str(e)}"
            )


    @staticmethod
    async def get_subscription_plans() -> Dict[str, Any]:
        """Get all subscription plans."""
        try:
            plans = razorpay_client.plan.all()
            return plans
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch plans: {str(e)}"
            )
