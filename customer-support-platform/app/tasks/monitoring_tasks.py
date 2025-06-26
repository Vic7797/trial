"""System monitoring and health check tasks."""
from datetime import datetime, timedelta
import psutil
from celery import shared_task
from celery.task.control import inspect

from app.core.database import AsyncSession
from app.core.logging import logger
from app.services.notification_service import NotificationService
from app.schemas.notifications import NotificationType


@shared_task(
    name="monitoring.check_system_health",
    queue="monitoring"
)
async def check_system_health_task() -> None:
    """Monitor system resources and alert if thresholds are exceeded."""
    try:
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:  # 80% threshold
            await _send_alert(
                "High CPU Usage",
                f"CPU usage is at {cpu_percent}%"
            )

        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 80:  # 80% threshold
            await _send_alert(
                "High Memory Usage",
                f"Memory usage is at {memory.percent}%"
            )

        # Check disk usage
        disk = psutil.disk_usage('/')
        if disk.percent > 80:  # 80% threshold
            await _send_alert(
                "High Disk Usage",
                f"Disk usage is at {disk.percent}%"
            )

    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        raise


@shared_task(
    name="monitoring.check_queue_health",
    queue="monitoring"
)
async def check_queue_health_task() -> None:
    """Monitor Celery queue health and task processing."""
    try:
        i = inspect()
        
        # Get queue statistics
        stats = i.stats()
        if not stats:
            await _send_alert(
                "Queue Health Check Failed",
                "Unable to get queue statistics"
            )
            return

        # Check for stuck tasks
        reserved = i.reserved()
        if reserved:
            for worker, tasks in reserved.items():
                for task in tasks:
                    # Alert if task has been reserved for too long
                    received = datetime.fromtimestamp(task['time_start'])
                    if datetime.now() - received > timedelta(hours=1):
                        await _send_alert(
                            "Stuck Task Detected",
                            f"Task {task['id']} on {worker} "
                            f"has been running for over an hour"
                        )

        # Check worker status
        active = i.active()
        if not active:
            await _send_alert(
                "No Active Workers",
                "No Celery workers are currently active"
            )

    except Exception as e:
        logger.error(f"Queue health check failed: {str(e)}")
        raise


async def _send_alert(title: str, message: str) -> None:
    """Send system alert to administrators."""
    async with AsyncSession() as db:
        service = NotificationService(db)
        try:
            await service.send_notification(
                NotificationType.SYSTEM_ALERT,
                None,  # Will be sent to all admins
                {
                    "title": title,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to send system alert: {str(e)}")
            raise
