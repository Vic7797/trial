from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.models.ticket import Ticket as TicketModel
from app.schemas.tickets import TicketCreate, TicketUpdate
from .base import CRUDBase

class CRUDTicket(CRUDBase[TicketModel, TicketCreate, TicketUpdate]):
    def get_with_details(
        self, 
        db: Session, 
        *, 
        ticket_id: str,
        organization_id: str
    ) -> Optional[TicketModel]:
        return (
            db.query(TicketModel)
            .options(
                joinedload(TicketModel.customer),
                joinedload(TicketModel.assigned_agent),
                joinedload(TicketModel.category),
                joinedload(TicketModel.messages)
            )
            .filter(
                TicketModel.id == ticket_id,
                TicketModel.organization_id == organization_id
            )
            .first()
        )
    
    def get_multi_by_organization(
        self, 
        db: Session, 
        *, 
        organization_id: str, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None,
        category_id: Optional[str] = None,
        assigned_agent_id: Optional[str] = None,
        customer_id: Optional[str] = None
    ) -> List[TicketModel]:
        query = db.query(TicketModel).filter(
            TicketModel.organization_id == organization_id
        )
        
        if status:
            query = query.filter(TicketModel.status == status)
        if category_id:
            query = query.filter(TicketModel.category_id == category_id)
        if assigned_agent_id:
            query = query.filter(TicketModel.assigned_agent_id == assigned_agent_id)
        if customer_id:
            query = query.filter(TicketModel.customer_id == customer_id)
            
        return (
            query
            .order_by(TicketModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_multi_by_agent(
        self, 
        db: Session, 
        *, 
        agent_id: str, 
        organization_id: str,
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[TicketModel]:
        query = db.query(TicketModel).filter(
            TicketModel.assigned_agent_id == agent_id,
            TicketModel.organization_id == organization_id
        )
        
        if status:
            query = query.filter(TicketModel.status == status)
            
        return (
            query
            .order_by(TicketModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_multi_by_customer(
        self, 
        db: Session, 
        *, 
        customer_id: str, 
        organization_id: str,
        skip: int = 0, 
        limit: int = 100
    ) -> List[TicketModel]:
        return (
            db.query(TicketModel)
            .filter(
                TicketModel.customer_id == customer_id,
                TicketModel.organization_id == organization_id
            )
            .order_by(TicketModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update_status(
        self, 
        db: Session, 
        *, 
        db_obj: TicketModel, 
        status: str
    ) -> TicketModel:
        db_obj.status = status
        now = datetime.utcnow()
        
        if status == 'resolved':
            db_obj.resolved_at = now
        elif status == 'closed':
            db_obj.closed_at = now
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def assign_agent(
        self, 
        db: Session, 
        *, 
        db_obj: TicketModel, 
        agent_id: str
    ) -> TicketModel:
        db_obj.assigned_agent_id = agent_id
        db_obj.assigned_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

ticket = CRUDTicket(TicketModel)
