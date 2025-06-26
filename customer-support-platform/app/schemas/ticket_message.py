from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, BaseCreate, BaseUpdate, BaseInDB

class TicketMessageBase(BaseSchema):
    ticket_id: UUID
    sender_type: str  # 'agent', 'customer', or 'system'
    sender_id: Optional[UUID] = None  # Optional for system messages
    message_content: str
    is_internal: bool = False


class TicketMessageCreate(TicketMessageBase, BaseCreate):
    pass  # Inherits all fields from base


class TicketMessageUpdate(BaseUpdate):
    message_content: Optional[str] = None
    is_internal: Optional[bool] = None


class TicketMessageInDB(TicketMessageBase, BaseInDB):
    # No additional fields needed as read/delivered tracking is handled by metadata
    pass


class TicketMessage(TicketMessageInDB):
    pass