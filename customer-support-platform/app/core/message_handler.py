"""Message queue handler for processing various message types."""
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.ticket_service import TicketService
from app.tasks.ai_tasks import (
    classify_ticket_task,
    auto_resolve_ticket_task,
    suggest_solutions_task
)
from app.tasks.notification_task import (
    send_email_response_task,
    send_telegram_response_task
)

logger = get_logger(__name__)


class MessageQueueHandler:
    """Handler for processing different types of messages from the queue."""

    @staticmethod
    async def handle_ticket_message(
        message: Dict[str, Any],
        background_tasks: Optional[BackgroundTasks] = None,
        db: Optional[AsyncSession] = None
    ) -> None:
        """
        Handle ticket-related messages from the queue.
        
        Args:
            message: Dictionary containing message data
            background_tasks: Optional BackgroundTasks for async scheduling
            db: Optional database session
            
        Message format:
        {
            "ticket_id": str,
            "action": str,  # "classify", "auto_resolve", "analyze", "notify"
            "metadata": dict  # Optional additional data
        }
        """
        try:
            ticket_id = message.get("ticket_id")
            action = message.get("action")
            metadata = message.get("metadata", {})

            if not ticket_id or not action:
                logger.error(
                    f"Invalid message format: missing ticket_id={ticket_id} "
                    f"or action={action}"
                )
                return

            if not db:
                async with AsyncSession() as db:
                    await MessageQueueHandler._process_ticket_action(
                        db, ticket_id, action, metadata
                    )
            else:
                await MessageQueueHandler._process_ticket_action(
                    db, ticket_id, action, metadata
                )

        except Exception as e:
            logger.error(
                f"Error processing ticket message: {str(e)}",
                exc_info=True,
                extra={
                    "ticket_id": ticket_id,
                    "action": action
                }
            )
            # Don't raise the exception - let the message queue handle retries
            
    @staticmethod
    async def _process_ticket_action(
        db: AsyncSession,
        ticket_id: str,
        action: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Process specific ticket action."""
        service = TicketService(db)
        
        try:
            if action == "classify":
                # Queue for classification
                task = await classify_ticket_task.delay(ticket_id)
                logger.info(
                    "Queued classification",
                    extra={"task_id": task.id, "ticket_id": ticket_id}
                )
                
            elif action == "auto_resolve":
                # Queue for auto-resolution with proper error handling
                task = await auto_resolve_ticket_task.delay(ticket_id)
                logger.info(
                    "Queued auto-resolution",
                    extra={"task_id": task.id, "ticket_id": ticket_id}
                )
                
            elif action == "analyze":
                # Handle ticket analysis with optional context
                context = metadata.get("context")
                task = await suggest_solutions_task.delay(ticket_id, context)
                logger.info(
                    "Queued analysis",
                    extra={"task_id": task.id, "ticket_id": ticket_id}
                )
                
            elif action == "notify":
                # Handle notifications based on ticket source
                await MessageQueueHandler._handle_notification(
                    ticket_id,
                    metadata
                )
                
            else:
                logger.warning(
                    "Unknown action",
                    extra={"action": action, "ticket_id": ticket_id}
                )

        except Exception as e:
            logger.error(
                f"Error processing ticket action: {str(e)}",
                exc_info=True,
                extra={
                    "ticket_id": ticket_id,
                    "action": action
                }
            )
            # If auto-processing fails, assign to human agent
            if action in ["auto_resolve", "analyze"]:
                await service.assign_to_available_agent(UUID(ticket_id))
            raise

    @staticmethod
    async def _handle_notification(
        ticket_id: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Handle sending notifications for different channels."""
        source = metadata.get("source")
        response = metadata.get("response")
        
        if not response:
            logger.error(
                "Missing response content",
                extra={"ticket_id": ticket_id}
            )
            return
            
        if source == "email":
            task = await send_email_response_task.delay(
                ticket_id=ticket_id,
                response=response
            )
            logger.info(
                "Queued email notification",
                extra={"task_id": task.id, "ticket_id": ticket_id}
            )
            
        elif source == "telegram":
            chat_id = metadata.get("chat_id")
            if chat_id:
                task = await send_telegram_response_task.delay(
                    chat_id=chat_id,
                    response=response
                )
                logger.info(
                    "Queued telegram notification",
                    extra={"task_id": task.id, "ticket_id": ticket_id}
                )
            else:
                logger.error(
                    "Missing chat_id for telegram notification",
                    extra={"ticket_id": ticket_id}
                )
        else:
            logger.warning(
                "Unknown notification source",
                extra={"source": source, "ticket_id": ticket_id}
            )

# Singleton instance for convenience


message_queue_handler = MessageQueueHandler()
