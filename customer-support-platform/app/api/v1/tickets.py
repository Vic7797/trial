"""Ticket management endpoints."""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from app.core.security import get_current_user, require_admin, require_agent
from app.schemas.tickets import (
    TicketResponse,
    TicketList,
    TicketUpdate,
    TicketMessage,
    TicketSearch,
    MessageEnhancement
)
from app.services.ticket_service import TicketService
from app.core.database import AsyncSession, get_db
from app.core.security import get_current_active_user

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("/", response_model=TicketList)
async def list_tickets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    page: int = Query(1, gt=0),
    per_page: int = Query(20, gt=0, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user=Depends(require_admin)
):
    """List all tickets (admin only)"""
    ticket_service = TicketService()
    return await ticket_service.list_tickets(
        status=status,
        category=category,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.get("/search", response_model=TicketSearch)
async def search_tickets(
    q: str = Query(..., min_length=3),
    category: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = Query(1, gt=0),
    per_page: int = Query(20, gt=0, le=100),
    current_user=Depends(get_current_user)
):
    """Search tickets with various filters"""
    ticket_service = TicketService()
    return await ticket_service.search_tickets(
        query=q,
        category=category,
        status=status,
        from_date=from_date,
        to_date=to_date,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
        user=current_user
    )


@router.get("/my-tickets", response_model=TicketList)
async def list_agent_tickets(
    status: Optional[str] = None,
    page: int = Query(1, gt=0),
    per_page: int = Query(20, gt=0, le=100),
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db)
):
    """List tickets assigned to current agent."""
    service = TicketService(db)
    return await service.list_agent_tickets(
        agent_id=current_user.id,
        status=status,
        page=page,
        per_page=per_page
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID = Path(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get ticket details."""
    service = TicketService(db)
    ticket = await service.get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
        
    # Check access permissions
    if not await service.can_access_ticket(current_user.id, ticket):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this ticket"
        )
        
    return ticket


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_data: TicketUpdate,
    ticket_id: UUID = Path(...),
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db)
):
    """Update ticket details."""
    service = TicketService(db)
    ticket = await service.get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
        
    # Check access permissions
    if not await service.can_access_ticket(current_user.id, ticket):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this ticket"
        )
        
    updated_ticket = await service.update_ticket(ticket_id, ticket_data)
    return updated_ticket


@router.post("/{ticket_id}/messages", response_model=TicketResponse)
async def add_ticket_message(
    message: TicketMessage,
    ticket_id: UUID = Path(...),
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db)
):
    """Add message to ticket."""
    service = TicketService(db)
    ticket = await service.get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
        
    # Check access permissions
    if not await service.can_access_ticket(current_user.id, ticket):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to message this ticket"
        )
        
    updated_ticket = await service.add_message(
        ticket_id,
        message,
        current_user.id
    )
    return updated_ticket


@router.get("/{ticket_id}/suggestions", response_model=List[str])
async def get_ticket_suggestions(
    ticket_id: UUID = Path(...),
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db)
):
    """Get AI-generated solution suggestions."""
    service = TicketService(db)
    ticket = await service.get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
        
    # Check access permissions
    if not await service.can_access_ticket(current_user.id, ticket):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to get suggestions for this ticket"
        )
        
    suggestions = await service.get_agent_suggestions(
        ticket_id,
        current_user.id
    )
    return suggestions


@router.post("/{ticket_id}/enhance", response_model=str)
async def enhance_message(
    enhancement_data: MessageEnhancement,
    ticket_id: UUID = Path(...),
    current_user=Depends(require_agent),
    db: AsyncSession = Depends(get_db)
):
    """Enhance message text using AI."""
    service = TicketService(db)
    ticket = await service.get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
        
    # Check access permissions
    if not await service.can_access_ticket(current_user.id, ticket):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to enhance messages for this ticket"
        )
        
    enhanced_text = await service.enhance_response(
        enhancement_data.text,
        enhancement_data.tone
    )
    return enhanced_text