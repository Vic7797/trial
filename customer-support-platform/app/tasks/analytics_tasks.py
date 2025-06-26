"""Analytics and reporting tasks."""
from celery import shared_task
from app.services.analytics_service import AnalyticsService
from app.models.analytics import TicketAnalytics

@celery_app.task
async def summarize_ticket_task(ticket_id: str):
    """Summarize ticket after resolution using analytics services."""
    AnalyticsService().summarize_ticket(ticket_id)
    TicketAnalytics.create_summary(ticket_id)

@celery_app.task
async def update_metrics_task():
    """Update analytics metrics periodically."""
    AnalyticsService().update_metrics()

@celery_app.task
async def generate_daily_report_task():
    """Generate daily analytics report."""
    AnalyticsService().generate_daily_report()
from app.core.database import AsyncSession


@shared_task(
    name="analytics.summarize_ticket",
    queue="analytics"
)
async def summarize_ticket_task(ticket_id: str):
    """Summarize resolved ticket for future reference."""
    async with AsyncSession() as db:
        service = AnalyticsService(db)
        await service.summarize_ticket(ticket_id)


@shared_task(
    name="analytics.update_metrics",
    queue="analytics"
)
async def update_metrics_task(org_id: str):
    """Update organization metrics."""
    async with AsyncSession() as db:
        service = AnalyticsService(db)
        await service.update_org_metrics(org_id)


@shared_task(
    name="analytics.daily_report",
    queue="analytics",
    retry_backoff=True,
    max_retries=2
)
async def generate_daily_report_task():
    """Generate daily analytics report."""
    async with AsyncSession() as db:
        service = AnalyticsService(db)
        await service.generate_daily_report()