from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_

from app.models.ticket_message import TicketMessage as TicketMessageModel
from app.schemas.ticket_message import TicketMessageCreate, TicketMessageUpdate
from .base import CRUDBase


class CRUDTicketMessage(CRUDBase[TicketMessageModel, TicketMessageCreate, TicketMessageUpdate]):
    def get_with_details(
        self,
        db: Session,
        *,
        message_id: str,
        organization_id: str
    ) -> Optional[TicketMessageModel]:
        return (
            db.query(TicketMessageModel)
            .options(
                joinedload(TicketMessageModel.ticket),
                joinedload(TicketMessageModel.sender)
            )
            .filter(
                TicketMessageModel.id == message_id,
                TicketMessageModel.organization_id == organization_id
            )
            .first()
        )
    
    def get_multi_by_ticket(
        self,
        db: Session,
        *,
        ticket_id: str,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
        include_internal: bool = False
    ) -> List[TicketMessageModel]:
        query = db.query(TicketMessageModel).filter(
            TicketMessageModel.ticket_id == ticket_id,
            TicketMessageModel.organization_id == organization_id
        )
        
        if not include_internal:
            query = query.filter(TicketMessageModel.is_internal == False)  # noqa: E712
            
        return (
            query
            .order_by(TicketMessageModel.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_multi_by_sender(
        self,
        db: Session,
        *,
        sender_id: str,
        organization_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[TicketMessageModel]:
        return (
            db.query(TicketMessageModel)
            .filter(
                TicketMessageModel.sender_id == sender_id,
                TicketMessageModel.organization_id == organization_id
            )
            .order_by(desc(TicketMessageModel.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_with_sender(
        self,
        db: Session,
        *,
        obj_in: TicketMessageCreate,
        ticket_id: str,
        sender_id: str,
        organization_id: str,
        is_internal: bool = False
    ) -> TicketMessageModel:
        db_obj = TicketMessageModel(
            **obj_in.dict(),
            ticket_id=ticket_id,
            sender_id=sender_id,
            organization_id=organization_id,
            is_internal=is_internal
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def mark_as_read(
        self,
        db: Session,
        *,
        db_obj: TicketMessageModel,
        user_id: str
    ) -> TicketMessageModel:
        if not db_obj.read_by:
            db_obj.read_by = {}
        
        db_obj.read_by[str(user_id)] = datetime.utcnow().isoformat()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_unread_count(
        self,
        db: Session,
        *,
        ticket_id: str,
        user_id: str,
        organization_id: str
    ) -> int:
        return (
            db.query(TicketMessageModel)
            .filter(
                TicketMessageModel.ticket_id == ticket_id,
                TicketMessageModel.organization_id == organization_id,
                or_(
                    TicketMessageModel.read_by == None,  # noqa: E711
                    ~TicketMessageModel.read_by.has_key(str(user_id))  # type: ignore
                ),
                TicketMessageModel.sender_id != str(user_id)
            )
            .count()
        )

ticket_message = CRUDTicketMessage(TicketMessageModel)

