"""Email polling and notification tasks."""
from celery import shared_task
from app.services.email_service import EmailService
from app.core.database import AsyncSession
from app.core.logging import logger


@shared_task(
    name="email.poll_inbox",
    queue="polling",
    retry_backoff=True,
    max_retries=3
)
async def poll_email_inbox_task():
    """Poll email inbox for new tickets."""
    async with AsyncSession() as db:
        service = EmailService(db)
        await service.poll_inbox()


@shared_task(
    name="email.send_response",
    queue="notifications",
    retry_backoff=True,
    max_retries=3
)
async def send_email_response_task(ticket_id: str, response: str):
    """Send email response for a ticket."""
    async with AsyncSession() as db:
        service = EmailService(db)
        await service.send_response(ticket_id, response)


@shared_task(
    name="email.send_welcome",
    queue="notifications"
)
async def send_welcome_email_task(user_id: str):
    """Send welcome email to new user."""
    async with AsyncSession() as db:
        service = EmailService(db)
        await service.send_welcome_email(user_id)