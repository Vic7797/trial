from celery.schedules import crontab
from app.tasks.email_tasks import poll_email_inbox_task
from app.tasks.telegram_tasks import poll_telegram_updates_task

CELERY_BEAT_SCHEDULE = {
    'poll-email-inbox': {
        'task': 'app.tasks.email_tasks.poll_email_inbox_task',
        'schedule': crontab(minute='*/2'),  # every 2 minutes
    },
    'poll-telegram-updates': {
        'task': 'app.tasks.telegram_tasks.poll_telegram_updates_task',
        'schedule': crontab(minute='*/2'),  # every 2 minutes
    },
}
