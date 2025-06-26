"""Ticket management service."""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from uuid import UUID

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from sqlalchemy import select

from app.core.logging import get_logger
from app.core.rate_limiter import rate_limit
from app.crud.tickets import ticket as ticket_crud
from app.crud.organizations import organization as org_crud
from app.crud import user as user_crud
from app.schemas.tickets import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketList,
    TicketMessage,
    TicketSearch,
    TicketClassification
)
from app.api.websockets import notify_ticket_created
from app.core.config import settings
from app.utils.validators import validate_ticket_limit
from app.core.message_queue import MessageQueue
from app.core.cache import Cache
from app.core.message_handler import message_queue_handler
from app.ai.crews import CrewFactory
from app.ai.vector_db import vector_db
from app.api.websockets import notify_ticket_updated, notify_message_added
from app.tasks.notification_tasks import send_notification_task


logger = get_logger(__name__)

class TicketService:
    """Service for ticket management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache_prefix = "ticket:"
        self.queue_prefix = "queue:"

    @rate_limit(
        key_prefix="ticket_creation",
        identifier=lambda r: str(r.user.id) if hasattr(r, 'user') else r.client.host
    )
    async def create_ticket(
        self,
        ticket_data: Union[TicketCreate, Dict[str, Any]],
        customer_id: Optional[UUID] = None,
        request: Optional[Request] = None
    ) -> TicketResponse:
        """Create a new ticket and trigger AI processing."""
        try:
            # Accept raw dicts coming from external services (e.g. Telegram)
            if not isinstance(ticket_data, TicketCreate):
                try:
                    ticket_data = TicketCreate(**ticket_data)  # type: ignore[arg-type]
                except Exception as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid ticket data: {exc}"
                    )

            # Fetch organization and plan
            org = await org_crud.get(self.db, id=ticket_data.organization_id)
            if not org:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found"
                )
            
            # Check plan limits
            plan = org.plan
            now = datetime.utcnow()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Get current month's ticket count
            ticket_count = await ticket_crud.count_by_organization_and_date(
                self.db,
                organization_id=ticket_data.organization_id,
                start_date=month_start
            )
            
            # Validate against plan limits
            validate_ticket_limit(ticket_count, plan)
                
            # Create ticket in database
            ticket = await ticket_crud.create(
                self.db,
                obj_in=TicketCreate(
                    subject=getattr(ticket_data, "subject", getattr(ticket_data, "title", "")),
                    description=ticket_data.description,
                    customer_id=customer_id,
                    channel=getattr(ticket_data, "channel", getattr(ticket_data, "source", "")),
                    status="new",
                    organization_id=ticket_data.organization_id
                )
            )

            # Queue for AI processing
            await self._queue_for_classification(ticket.id)
            
            # Send WebSocket notification
            await notify_ticket_created(
                org_id=ticket.organization_id,
                ticket_id=ticket.id,
                ticket_data=ticket.dict()
            )
            
            return ticket
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticket creation failed: {str(e)}"
            )

    async def _queue_for_classification(self, ticket_id: UUID):
        """Queue ticket for AI classification."""
        await MessageQueue.publish(
            "tickets",
            {
                "ticket_id": str(ticket_id),
                "action": "classify"
            }
        )

    async def classify_ticket(self, ticket_id: UUID) -> TicketClassification:
        """Use AI crew to classify ticket criticality and category."""
        ticket = await self.get_ticket(ticket_id)
        
        # Use AI crew for classification
        crew = CrewFactory.get_classification_crew()
        result = await crew.classify_ticket(
            ticket.title,
            ticket.description,
            str(ticket.organization_id)
        )
        
        classification = TicketClassification(**result)

        # Update ticket with classification
        await self.update_ticket(
            ticket_id,
            TicketUpdate(
                category_id=classification.category_id,
                criticality=classification.criticality,
                estimated_time=classification.estimated_time
            )
        )

        # Queue for resolution if low criticality
        if classification.criticality == "low":
            await self._queue_for_auto_resolution(ticket_id)
        else:
            await self._assign_to_agent(ticket_id)

        return classification

    async def _queue_for_auto_resolution(self, ticket_id: UUID):
        """Queue low criticality ticket for automatic resolution."""
        await MessageQueue.publish(
            "tickets",
            {
            "ticket_id": str(ticket_id),
            "action": "auto_resolve"
        }, db=self.db)

    async def _assign_to_agent(self, ticket_id: UUID):
        """Assign ticket to available agent."""
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Update ticket status
        await self.update_ticket(
            ticket_id,
            TicketUpdate(
                status="pending",
                assigned_at=datetime.utcnow()
            )
        )
        # Find and assign to available agent
        await self.assign_to_available_agent(ticket_id)

    async def get_auto_resolution(self, ticket_id: str) -> str:
        """Get automatic resolution from vector database using CrewAI.
        
        Args:
            ticket_id: The ticket ID to resolve
            
        Returns:
            str: The suggested resolution
        """
        ticket = await self.get_ticket(UUID(ticket_id))
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
            
        # Get relevant documents from vector database
        documents = await vector_db.search(
            query=f"{ticket.title}\n{ticket.description}",
            category=ticket.category.name if ticket.category else None,
            n_results=3
        )
        
        # Use CrewAI to generate solution
        crew = CrewFactory.get_solution_crew()
        solution = await crew.generate_solution(
            ticket.title,
            ticket.description,
            [doc.page_content for doc in documents]
        )
        
        return solution

    async def enhance_response(
        self,
        text: str,
        tone: str = "professional"
    ) -> str:
        """Enhance response text using CrewAI.
        
        Args:
            text: The text to enhance
            tone: The tone to use (professional, friendly, etc.)
            
        Returns:
            str: Enhanced text
        """
        crew = CrewFactory.get_enhancement_crew()
        return await crew.enhance_text(text, tone)

    async def assign_to_available_agent(self, ticket_id: UUID):
        """Assign the ticket to an available agent using round-robin fairness."""
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Retrieve all active agents for the organization
        agents = await user_crud.get_multi_active_agents(
            self.db,
            organization_id=ticket.organization_id
        )
        if ticket.category_id:
            agents = [
                agent for agent in agents 
                if any(assign.category_id == ticket.category_id 
                       for assign in getattr(agent, "category_assignments", []))
            ]
            
            if not agents:
                logger.warning(
                    f"No agents available for category {ticket.category_id} in ticket {ticket_id}"
                )
                return

        if not agents:
            logger.warning("No available active agents for ticket %s", ticket_id)
            return

        # Select agent with fewest active tickets; tiebreaker -> earliest last_assigned_at
        selected_agent = None
        min_tickets = float("inf")
        earliest_last_assigned: Optional[datetime] = None

        for agent in agents:
            active_cnt = await self.get_agent_active_tickets_count(agent.id)
            last_assigned = agent.last_assigned_at or datetime.min

            if (active_cnt < min_tickets or
                (active_cnt == min_tickets and (
                    earliest_last_assigned is None or last_assigned < earliest_last_assigned))):
                selected_agent = agent
                min_tickets = active_cnt
                earliest_last_assigned = last_assigned

        if not selected_agent:
            logger.warning("Agent selection failed for ticket %s", ticket_id)
            return

        # Update ticket in DB
        await self.update_ticket(
            ticket_id,
            TicketUpdate(
                assigned_agent_id=selected_agent.id,
                status="assigned",
                assigned_at=datetime.utcnow()
            )
        )

        # Stamp agent
        await user_crud.update(
            self.db,
            db_obj=selected_agent,
            obj_in={"last_assigned_at": datetime.utcnow()}
        )

        # Notify agent asynchronously
        await send_notification_task.delay(
            notification_type="ticket_assigned",
            recipient_id=str(selected_agent.id),
            data={
                "ticket_id": str(ticket_id),
                "ticket_title": getattr(ticket, "subject", getattr(ticket, "title", ""))
            }
        )
        """Assign ticket to an available agent using round-robin."""
        ticket = await self.get_ticket(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Get available agents (status='active')
        agents = await user_crud.get_multi_active_agents(
            self.db,
            organization_id=ticket.organization_id
        )
        # Filter agents with status='active' if not already filtered
        agents = [a for a in agents if getattr(a, 'status', 'active') == 'active']

        if not agents:
            logger.warning(f"No available active agents for ticket {ticket_id}")
            return
        
        # Select agent using round-robin
        selected_agent = None
        min_tickets = float('inf')
        min_last_assigned = None
        

        
    async def get_agent_active_tickets_count(self, agent_id: UUID) -> int:
        """Return count of active (unresolved) tickets assigned to the agent."""
        from app.models.tickets import Ticket as TicketModel

        active_statuses = {"new", "open", "pending", "assigned", "in_progress"}
        result = await self.db.execute(
            select(func.count()).select_from(TicketModel).where(
                TicketModel.assigned_agent_id == agent_id,
                TicketModel.status.in_(active_statuses)
            )
        )
        return result.scalar_one() or 0

    async def get_ticket(self, ticket_id: UUID) -> TicketResponse:
        """Get ticket by ID with caching."""
        cache_key = f"{self.cache_prefix}{str(ticket_id)}"
        
        # Try cache first
        cached_ticket = await Cache.get(cache_key)
        if cached_ticket:
            return TicketResponse(**cached_ticket)

        # Cache miss, get from database
        ticket = await ticket_crud.get(self.db, id=ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )

        # Cache the result
        await Cache.set(cache_key, ticket.dict())
        return ticket

    async def get_agent_suggestions(
        self,
        ticket_id: UUID,
        agent_id: UUID
    ) -> List[str]:
        """Get AI-generated response suggestions for agent."""
        ticket = await self.get_ticket(ticket_id)
        
        # Use SolutionCrew through CrewFactory
        result = CrewFactory.generate_solution(
            ticket_title=ticket.title,
            ticket_description=ticket.description,
            ticket_category=ticket.category.name if ticket.category else 'Uncategorized',
            ticket_criticality=ticket.criticality,
            num_variants=3  # Get 3 different suggestions
        )
        
        # Extract solutions from result
        if isinstance(result.get('solutions'), list):
            return [sol['solution'] for sol in result['solutions']]
        elif 'solution' in result:
            return [result['solution']]
        else:
            return ["Unable to generate suggestions at this time."]

    async def enhance_response(self, response: str) -> str:
        """Enhance response using AI."""
        # Use EnhancementCrew through CrewFactory
        result = CrewFactory.enhance_response(
            response=response,
            enhancement_type='grammar'  # This will enhance both grammar and tone
        )
        
        # Return the enhanced text directly
        return result

    async def update_ticket(
        self,
        ticket_id: UUID,
        ticket_data: TicketUpdate
    ) -> TicketResponse:
        """Update ticket and invalidate cache."""
        current_ticket = await self.get_ticket(ticket_id)
        
        try:
            updated_ticket = await ticket_crud.update(
                self.db,
                db_obj=current_ticket,
                obj_in=ticket_data
            )
            
            # Invalidate cache
            cache_key = f"{self.cache_prefix}{str(ticket_id)}"
            await Cache.delete(cache_key)
            
            # Send WebSocket notification
            await notify_ticket_updated(
                org_id=updated_ticket.organization_id,
                ticket_id=updated_ticket.id,
                ticket_data=updated_ticket.dict()
            )
            
            return updated_ticket
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticket update failed: {str(e)}"
            )

    async def resolve_ticket(self, ticket_id: UUID) -> TicketResponse:
        """Mark ticket as resolved and trigger analysis."""
        try:
            ticket = await self.update_ticket(
                ticket_id,
                TicketUpdate(
                    status="resolved",
                    resolved_at=datetime.utcnow()
                )
            )

            # Queue for analysis
            await self._queue_for_analysis(ticket_id)
            return ticket
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticket resolution failed: {str(e)}"
            )

    async def _queue_for_analysis(self, ticket_id: UUID):
        """Queue resolved ticket for AI analysis."""
        await MessageQueue.publish(
            "tickets",
            {
                "ticket_id": str(ticket_id),
                "action": "analyze"
            }
        )

    async def analyze_resolved_ticket(self, ticket_id: UUID) -> Dict[str, Any]:
        """Analyze resolved ticket for insights."""
        ticket = await self.get_ticket(ticket_id)
        
        # Calculate resolution time in hours
        resolution_time = (ticket.resolved_at - ticket.created_at).total_seconds() / 3600
        
        # Use AnalysisCrew through CrewFactory
        analysis = CrewFactory.analyze_ticket(
            ticket_title=ticket.title,
            ticket_description=ticket.description,
            ticket_category=ticket.category.name if ticket.category else 'Uncategorized',
            ticket_resolution=ticket.resolution,
            resolution_time_hours=resolution_time,
            customer_satisfaction_rating=ticket.satisfaction_rating
        )
        
        return {
            "ticket_id": str(ticket_id),
            "analysis": analysis,
            "analyzed_at": datetime.utcnow()
        }

    async def add_message(
        self,
        ticket_id: UUID,
        message_data: dict,
        sender_id: UUID
    ) -> TicketResponse:
        """Add a message to a ticket."""
        try:
            ticket = await self.get_ticket(ticket_id)
            
            # Create message
            message = await ticket_message_crud.create_with_sender(
                self.db,
                obj_in=message_data,
                ticket_id=str(ticket_id),
                sender_id=str(sender_id),
                organization_id=str(ticket.organization_id)
            )
            
            # Send WebSocket notification
            await notify_message_added(
                org_id=ticket.organization_id,
                ticket_id=ticket_id,
                message_data=message.dict()
            )
            
            return ticket
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to add message: {str(e)}"
            )