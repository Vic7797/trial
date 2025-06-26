from fastapi import APIRouter, Depends, Query
from app.core.security import require_admin
from app.schemas.payments import (
    OrderCreate,
    OrderResponse,
    PaymentVerification,
    TransactionList
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/create-order", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user=Depends(require_admin)
):
    """Create a new Razorpay order (admin only)"""
    payment_service = PaymentService()
    return await payment_service.create_order(
        organization_id=current_user.organization_id,
        order_data=order_data
    )


@router.post("/verify-payment", response_model=OrderResponse)
async def verify_payment(
    verification: PaymentVerification,
    current_user=Depends(require_admin)
):
    """Verify Razorpay payment (admin only)"""
    payment_service = PaymentService()
    return await payment_service.verify_payment(
        organization_id=current_user.organization_id,
        verification_data=verification
    )


@router.get("/transactions", response_model=TransactionList)
async def list_transactions(
    page: int = Query(1, gt=0),
    per_page: int = Query(20, gt=0, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user=Depends(require_admin)
):
    """List payment transactions (admin only)"""
    payment_service = PaymentService()
    return await payment_service.list_transactions(
        organization_id=current_user.organization_id,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order
    )