from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.payment import PaymentTransaction as PaymentTransactionModel
from app.schemas.payments import (
    PaymentTransactionCreate,
    PaymentTransactionUpdate,
)
from .base import CRUDBase


class CRUDPayment(CRUDBase[PaymentTransactionModel, PaymentTransactionCreate, PaymentTransactionUpdate]):
    def get_by_razorpay_id(
        self,
        db: Session,
        *,
        razorpay_payment_id: str,
        organization_id: Optional[str] = None
    ) -> Optional[PaymentTransactionModel]:
        query = db.query(PaymentTransactionModel).filter(
            PaymentTransactionModel.razorpay_payment_id == razorpay_payment_id
        )
        if organization_id:
            query = query.filter(PaymentTransactionModel.organization_id == organization_id)
        return query.first()

    def get_by_order_id(
        self,
        db: Session,
        *,
        razorpay_order_id: str,
        organization_id: Optional[str] = None
    ) -> Optional[PaymentTransactionModel]:
        query = db.query(PaymentTransactionModel).filter(
            PaymentTransactionModel.razorpay_order_id == razorpay_order_id
        )
        if organization_id:
            query = query.filter(PaymentTransactionModel.organization_id == organization_id)
        return query.first()

    def get_multi_by_organization(
        self,
        db: Session,
        *,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[PaymentTransactionModel]:
        query = db.query(PaymentTransactionModel).filter(
            PaymentTransactionModel.organization_id == organization_id
        )

        if status:
            query = query.filter(
                PaymentTransactionModel.status == status.lower()
            )

        if start_date:
            query = query.filter(
                PaymentTransactionModel.created_at >= start_date
            )

        if end_date:
            # Include the entire end date
            next_day = datetime.combine(
                end_date, datetime.min.time()
            ) + timedelta(days=1)
            query = query.filter(
                PaymentTransactionModel.created_at < next_day
            )

        return (
            query
            .order_by(PaymentTransactionModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_status(
        self,
        db: Session,
        *,
        db_obj: PaymentTransactionModel,
        status: str,
        razorpay_payment_id: Optional[str] = None,
        update_data: Optional[Dict[str, Any]] = None
    ) -> PaymentTransactionModel:
        db_obj.status = status.lower()
        
        if razorpay_payment_id:
            db_obj.razorpay_payment_id = razorpay_payment_id
            
        if update_data:
            for field, value in update_data.items():
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_total_paid_amount(
        self,
        db: Session,
        *,
        organization_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Decimal:
        query = db.query(PaymentTransactionModel).filter(
            PaymentTransactionModel.organization_id == organization_id,
            PaymentTransactionModel.status == 'captured'
        )
        
        if start_date:
            query = query.filter(PaymentTransactionModel.created_at >= start_date)
            
        if end_date:
            next_day = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)
            query = query.filter(PaymentTransactionModel.created_at < next_day)
        
        result = query.with_entities(
            db.func.coalesce(db.func.sum(PaymentTransactionModel.amount), Decimal('0'))
        ).scalar()
        
        return result if result is not None else Decimal('0')
    
    def has_active_subscription(
        self,
        db: Session,
        *,
        organization_id: str,
        current_date: Optional[date] = None
    ) -> bool:
        if current_date is None:
            current_date = date.today()
            
        return db.query(
            db.query(PaymentTransactionModel)
            .filter(
                PaymentTransactionModel.organization_id == organization_id,
                PaymentTransactionModel.status == 'captured',
                PaymentTransactionModel.billing_period_start <= current_date,
                PaymentTransactionModel.billing_period_end >= current_date
            )
            .exists()
        ).scalar()


# Create a singleton instance
payment = CRUDPayment(PaymentTransactionModel)
