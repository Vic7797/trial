"""AI-related tasks for ticket processing and document handling."""
from uuid import UUID
from datetime import datetime

from celery import shared_task

from app.core.database import AsyncSession
from app.core.logging import logger
from app.services.ticket_service import TicketService
from app.services.document_service import DocumentService
from app.schemas.tickets import TicketUpdate
from app.tasks.email_tasks import send_email_response_task
from app.tasks.telegram_tasks import send_telegram_response_task


@shared_task(
    name="ai.classify_ticket",
    queue="classification",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3
)
async def classify_ticket_task(ticket_id: str) -> None:
    """Classify ticket and determine criticality using CrewAI.
    
    Args:
        ticket_id: ID of the ticket to classify
    """
    async with AsyncSession() as db:
        service = TicketService(db)
        await service.classify_ticket(ticket_id)


@shared_task(
    name="ai.process_document",
    queue="processing",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2
)
async def process_document_task(document_id: str) -> None:
    """Process document for vector storage.
    
    Args:
        document_id: ID of the document to process
    """
    async with AsyncSession() as db:
        service = DocumentService(db)
        await service.process_document(document_id)


@shared_task(
    name="ai.suggest_solutions",
    queue="processing",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2
)
async def suggest_solutions_task(ticket_id: str, agent_id: str) -> dict:
    """Get solution suggestions using CrewAI.

    Args:
        ticket_id: ID of the ticket to get suggestions for
        agent_id: ID of the agent requesting suggestions
        
    Returns:
        dict: Status and suggestions or error message
    """
    async with AsyncSession() as db:
        try:
            service = TicketService(db)
            suggestions = await service.get_agent_suggestions(
                ticket_id=UUID(ticket_id),
                agent_id=UUID(agent_id)
            )
            return {"status": "success", "suggestions": suggestions}
        except Exception as e:
            import sentry_sdk
            sentry_sdk.capture_exception(e)
            logger.error("Error generating suggestions: %s", str(e))
            return {"status": "error", "message": str(e)}


@shared_task(
    name="ai.enhance_response",
    queue="processing"
)
async def enhance_response_task(text: str, tone: str = "professional") -> str:
    """Enhance response text using CrewAI.
    
    Args:
        text: The text to enhance
        tone: The tone to use for enhancement (default: professional)
        
    Returns:
        str: Enhanced text
    """
    async with AsyncSession() as db:
        service = TicketService(db)
        return await service.enhance_response(text, tone)


@shared_task(
    name="ai.auto_resolve_ticket",
    queue="processing",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3
)
async def auto_resolve_ticket_task(ticket_id: str) -> dict:
    """Automatically resolve a low criticality ticket using CrewAI.
    
    Args:
        ticket_id: ID of the ticket to resolve
        
    Returns:
        dict: Status and resolution details
    """
    async with AsyncSession() as db:
        try:
            service = TicketService(db)
            ticket = await service.get_ticket(UUID(ticket_id))
            
            if not ticket:
                raise ValueError(f"Ticket {ticket_id} not found")
            
            # Get solution from vector database and enhance it
            solution = await service.get_auto_resolution(ticket_id)
            enhanced_solution = await service.enhance_response(
                solution,
                tone="professional"
            )
            
            # Update ticket with resolution
            await service.update_ticket(
                UUID(ticket_id),
                TicketUpdate(
                    status="resolved",
                    resolution=enhanced_solution,
                    resolved_at=datetime.utcnow(),
                    resolution_type="auto"
                )
            )
            
            # Send response based on ticket source
            if ticket.source == "email":
                await send_email_response_task.delay(
                    ticket_id=ticket_id,
                    response=enhanced_solution
                )
            elif ticket.source == "telegram":
                await send_telegram_response_task.delay(
                    chat_id=ticket.source_metadata["chat_id"],
                    response=enhanced_solution
                )
            
            return {
                "status": "success",
                "ticket_id": ticket_id,
                "resolution": enhanced_solution
            }

        except Exception as e:
            logger.error(
                f"Auto-resolution failed for ticket {ticket_id}: {str(e)}",
                exc_info=True
            )
            # After max retries, the ticket will be assigned to a human agent
            await service.assign_to_available_agent(UUID(ticket_id))
            raise
