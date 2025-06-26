"""Cleanup and maintenance tasks."""
from celery import shared_task
from app.services.document_service import DocumentService
from app.services.ticket_service import TicketService
from app.core.database import AsyncSession


@shared_task(
    name="cleanup.archive_tickets",
    queue="default",
    soft_time_limit=7200,  # 2 hour timeout
    time_limit=7200
)
async def archive_old_tickets_task(days: int = 30):
    """Archive tickets older than specified days."""
    async with AsyncSession() as db:
        service = TicketService(db)
        await service.archive_old_tickets(days)


@shared_task(
    name="cleanup.cleanup_temp_files",
    queue="default",
    soft_time_limit=1800,  # 30 minute timeout
    time_limit=1800
)
async def cleanup_temp_files_task():
    """Clean up temporary files."""
    async with AsyncSession() as db:
        service = DocumentService(db)
        await service.cleanup_temp_files()


@shared_task(
    name="cleanup.verify_storage",
    queue="default",
    soft_time_limit=3600,  # 1 hour timeout
    time_limit=3600
)
async def verify_storage_integrity_task():
    """Verify storage integrity between DB, MinIO and vector database."""
    async with AsyncSession() as db:
        service = DocumentService(db)
        await service.verify_storage_integrity()

