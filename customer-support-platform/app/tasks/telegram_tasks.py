"""Telegram bot polling and notification tasks."""
from celery import shared_task
from app.services.telegram_service import TelegramService
from app.core.database import AsyncSession


@shared_task(
    name="telegram.poll_updates",
    queue="polling",
    retry_backoff=True,
    max_retries=3
)
async def poll_telegram_updates_task():
    """Poll telegram for new messages/tickets."""
    async with AsyncSession() as db:
        service = TelegramService(db)
        await service.poll_updates()


@shared_task(
    name="telegram.send_response",
    queue="notifications",
    retry_backoff=True,
    max_retries=3
)
async def send_telegram_response_task(chat_id: str, response: str):
    """Send telegram response for a ticket."""
    async with AsyncSession() as db:
        service = TelegramService(db)
        await service.send_message(chat_id, response)