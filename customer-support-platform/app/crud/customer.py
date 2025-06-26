from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.customer import Customer as CustomerModel
from app.schemas.customer import CustomerCreate, CustomerUpdate
from .base import CRUDBase

class CRUDCustomer(CRUDBase[CustomerModel, CustomerCreate, CustomerUpdate]):
    def get_by_email(
        self, 
        db: Session, 
        *, 
        email: str, 
        organization_id: str
    ) -> Optional[CustomerModel]:
        return (
            db.query(CustomerModel)
            .filter(
                CustomerModel.email == email,
                CustomerModel.organization_id == organization_id
            )
            .first()
        )

    def get_by_channel_identifier(
        self, 
        db: Session, 
        *, 
        channel: str, 
        channel_identifier: str, 
        organization_id: str
    ) -> Optional[CustomerModel]:
        return (
            db.query(CustomerModel)
            .filter(
                CustomerModel.channel == channel,
                CustomerModel.channel_identifier == channel_identifier,
                CustomerModel.organization_id == organization_id
            )
            .first()
        )

    def search(
        self, 
        db: Session, 
        *, 
        search_term: str, 
        organization_id: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[CustomerModel]:
        return (
            db.query(CustomerModel)
            .filter(
                CustomerModel.organization_id == organization_id,
                or_(
                    CustomerModel.email.ilike(f"%{search_term}%"),
                    CustomerModel.name.ilike(f"%{search_term}%"),
                    CustomerModel.phone.ilike(f"%{search_term}%")
                )
            )
            .order_by(CustomerModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_multi_by_organization(
        self, 
        db: Session, 
        *, 
        organization_id: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[CustomerModel]:
        return (
            db.query(CustomerModel)
            .filter(CustomerModel.organization_id == organization_id)
            .order_by(CustomerModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_tickets(
        self, db: Session, *, customer_id: str, organization_id: str, skip: int = 0, limit: int = 100
    ) -> List[Customer]:
        customer = (
            db.query(Customer)
            .options(joinedload(Customer.tickets))
            .filter(
                Customer.id == customer_id,
                Customer.organization_id == organization_id
            )
            .first()
        )
        return customer.tickets[skip:skip + limit] if customer else []

customer = CRUDCustomer(Customer)
