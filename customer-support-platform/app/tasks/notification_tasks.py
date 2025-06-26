"""Notification and alerting tasks."""
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from app.core.database import AsyncSession
from app.core.logging import logger
from app.services.notification_service import NotificationService
from app.services.organization_service import OrganizationService
from app.models.core import Organization
from app.schemas.notifications import NotificationType


@shared_task(
    name="notifications.send_notification",
    queue="notifications",
    retry_backoff=True,
    max_retries=3
)
async def send_notification_task(
    notification_type: str,
    recipient_id: str,
    data: Dict[str, Any]
) -> bool:
    """Send a notification through appropriate channels."""
    async with AsyncSession() as db:
        service = NotificationService(db)
        try:
            return await service.send_notification(
                NotificationType(notification_type),
                UUID(recipient_id),
                data
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            raise


@shared_task(
    name="notifications.check_plan_expiry",
    queue="notifications"
)
async def check_plan_expiry_task() -> None:
    """Check for expiring plans and send notifications."""
    async with AsyncSession() as db:
        service = OrganizationService(db)
        try:
            # Get organizations with plans expiring in next 7 days
            expiry_date = datetime.utcnow() + timedelta(days=7)
            query = select(Organization).where(
                Organization.plan_expires_at <= expiry_date,
                Organization.plan_expires_at > datetime.utcnow()
            )
            result = await db.execute(query)
            orgs = result.scalars().all()

            for org in orgs:
                await send_notification_task.delay(
                    notification_type=NotificationType.PLAN_EXPIRING.value,
                    recipient_id=str(org.id),
                    data={
                        "plan_name": org.plan,
                        "days_left": (
                            org.plan_expires_at - datetime.utcnow()
                        ).days,
                        "email": org.admin_email
                    }
                )
        except Exception as e:
            import sentry_sdk
            sentry_sdk.capture_exception(e)
            logger.error(f"Failed to check plan expiry: {str(e)}")
            raise


@shared_task(
    name="notifications.process_notification_queue",
    queue="notifications",
    rate_limit="100/m"
)
async def process_notification_queue_task() -> None:
    """Process pending notifications in the queue."""
    async with AsyncSession() as db:
        service = NotificationService(db)
        try:
            await service.process_notification_queue()
        except Exception as e:
            logger.error(
                f"Failed to process notification queue: {str(e)}"
            )
            raise


@shared_task(
    name="notifications.cleanup_old_notifications",
    queue="notifications"
)
async def cleanup_old_notifications_task(days: int = 30) -> None:
    """Clean up notifications older than specified days."""
    async with AsyncSession() as db:
        service = NotificationService(db)
        try:
            await service.cleanup_old_notifications(days)
        except Exception as e:
            logger.error(f"Failed to cleanup notifications: {str(e)}")
            raise