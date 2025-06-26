# Export all tasks for easier imports
from .ai_tasks import (
    classify_ticket_task,
    process_document_task,
    suggest_solutions_task,
    enhance_response_task
)
from .analytics_tasks import (
    summarize_ticket_task,
    update_metrics_task,
    generate_daily_report_task
)
from .cleanup_tasks import (
    archive_old_tickets_task,
    cleanup_temp_files_task,
    verify_storage_integrity_task
)
from .email_tasks import (
    poll_email_inbox_task,
    send_email_response_task,
    send_welcome_email_task
)
from .notification_tasks import (
    send_notification_task,
    check_plan_expiry_task,
    process_notification_queue_task,
    cleanup_old_notifications_task
)
from .telegram_tasks import (
    poll_telegram_updates_task,
    send_telegram_response_task
)
from .monitoring_tasks import (
    check_system_health_task,
    check_queue_health_task
)

# Make all tasks available when importing from app.tasks
__all__ = [
    # AI Tasks
    'classify_ticket_task',
    'process_document_task',
    'suggest_solutions_task',
    'enhance_response_task',
    # Analytics Tasks
    'summarize_ticket_task',
    'update_metrics_task',
    'generate_daily_report_task',
    # Cleanup Tasks
    'archive_old_tickets_task',
    'cleanup_temp_files_task',
    'verify_storage_integrity_task',
    # Email Tasks
    'poll_email_inbox_task',
    'send_email_response_task',
    'send_welcome_email_task',
    # Notification Tasks
    'send_notification_task',
    'check_plan_expiry_task',
    'process_notification_queue_task',
    'cleanup_old_notifications_task',
    # Telegram Tasks
    'poll_telegram_updates_task',
    'send_telegram_response_task',
    # Monitoring Tasks
    'check_system_health_task',
    'check_queue_health_task'
]
