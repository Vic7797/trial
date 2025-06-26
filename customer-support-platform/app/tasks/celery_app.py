"""Celery application configuration."""
from celery import Celery
from celery.signals import task_failure, worker_ready
import sentry_sdk
from kombu import Exchange, Queue

from app.core.config import settings
from app.core.logging import logger


# Initialize Sentry for task monitoring
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE
    )

# Create Celery app
app = Celery(
    'customer_support',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'app.tasks.ai_tasks',
        'app.tasks.analytics_tasks',
        'app.tasks.cleanup_tasks',
        'app.tasks.email_tasks',
        'app.tasks.notification_tasks',
        'app.tasks.telegram_tasks',
        'app.tasks.monitoring_tasks'
    ]
)

# Configure Celery
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    worker_max_memory_per_child=200000,  # 200MB
    
    # Result backend settings
    result_backend=settings.CELERY_RESULT_BACKEND,
    result_extended=True,
    result_expires=3600,  # 1 hour
    
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=3,
    
    # Add database_uri to the config
    database_uri=os.getenv('SQLALCHEMY_DATABASE_URI', '')
)

def _create_queue(name, exchange, routing_key, **kwargs):
    return Queue(
        name,
        Exchange(exchange),
        routing_key=routing_key,
        **kwargs
    )


task_queues = [
    _create_queue('critical', 'critical', 'critical',
                 queue_arguments={'x-max-priority': 10}),
    _create_queue('notifications_high', 'notifications_high',
                 'notifications.high',
                 queue_arguments={'x-max-priority': 10}),
    _create_queue('default', 'default', 'default',
                 queue_arguments={'x-max-priority': 10}),
    _create_queue('classification', 'classification',
                 'classification',
                 queue_arguments={'x-max-priority': 10}),
    _create_queue('processing', 'processing', 'processing',
                 queue_arguments={'x-max-priority': 10}),
    _create_queue('notifications', 'notifications', 'notifications',
                 queue_arguments={'x-max-priority': 10}),
    _create_queue('analytics', 'analytics', 'analytics',
                 queue_arguments={'x-max-priority': 10}),
    _create_queue('polling', 'polling', 'polling',
                 queue_arguments={'x-max-priority': 10}),
    _create_queue('monitoring', 'monitoring', 'monitoring'),
    _create_queue('dead_letter', 'dead_letter', 'dead_letter')
]

# Add database_uri to the Celery config
app.conf.database_uri = settings.SQLALCHEMY_DATABASE_URI

# Configure Celery
app.conf.update(
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=3,
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    enable_utc=True,
    timezone='UTC',
    
    # Queue settings
    task_queues=task_queues,
    task_default_queue='default',
    task_routes=settings.CELERY_TASK_ROUTES,
    
    # Result backend settings
    result_expires=3600,  # Results expire in 1 hour
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=settings.WORKERS_COUNT,
    task_default_priority=5,
    task_queue_max_priority=10,
    
    task_routes={
        # High priority tasks
        'app.tasks.notification_tasks.send_critical_notification': {
            'queue': 'critical',
            'routing_key': 'critical'
        },
        
        # AI tasks
        'app.tasks.ai_tasks.classify_ticket': {
            'queue': 'classification',
            'routing_key': 'classification'
        },
        'app.tasks.ai_tasks.auto_resolve_ticket': {
            'queue': 'processing',
            'routing_key': 'processing',
            'priority': 5
        },
        'app.tasks.ai_tasks.suggest_solutions': {
            'queue': 'processing',
            'routing_key': 'processing',
            'priority': 3
        },
        'app.tasks.ai_tasks.enhance_response': {
            'queue': 'processing',
            'routing_key': 'processing',
            'priority': 4
        },
        
        # Notification tasks
        'app.tasks.notification_tasks.*': {
            'queue': 'notifications',
            'routing_key': 'notifications'
        },
        'app.tasks.email_tasks.*': {
            'queue': 'notifications',
            'routing_key': 'notifications'
        },
        'app.tasks.telegram_tasks.*': {
            'queue': 'notifications',
            'routing_key': 'notifications'
        },
        
        # Analytics and cleanup
        'app.tasks.analytics_tasks.*': {
            'queue': 'analytics',
            'routing_key': 'analytics',
            'priority': 8
        },
        'app.tasks.cleanup_tasks.*': {
            'queue': 'analytics',
            'routing_key': 'analytics',
            'priority': 9
        }
    },
    
    task_annotations={
        '*': {
            'rate_limit': '10/s',
            'max_retries': 3,
            'default_retry_delay': 60,
            'acks_late': True
        },
        'app.tasks.notification_tasks.send_critical_notification': {
            'priority': 10,
            'max_retries': 5,
            'rate_limit': '100/m'
        },
        'app.tasks.ai_tasks.auto_resolve_ticket': {
            'priority': 5,
            'max_retries': 3,
            'time_limit': 300  # 5 minutes
        },
        'app.tasks.ai_tasks.classify_ticket': {
            'priority': 7,
            'max_retries': 3,
            'time_limit': 60  # 1 minute
        }
    }
)

# Register task modules
app.autodiscover_tasks([
    'app.tasks.ai_tasks',
    'app.tasks.analytics_tasks',
    'app.tasks.cleanup_tasks',
    'app.tasks.email_tasks',
    'app.tasks.notification_tasks',
    'app.tasks.telegram_tasks',
    'app.tasks.monitoring_tasks'
])

# Error handling
@task_failure.connect
def handle_task_failure(task_id, exception, args, kwargs, traceback, **kw):
    """Handle task failures and log errors."""
    logger.error(
        f"Task {task_id} failed: {exception}\n"
        f"Args: {args}\nKwargs: {kwargs}\n"
        f"Traceback: {traceback}"
    )

# Worker ready handler
@worker_ready.connect
def handle_worker_ready(sender, **kwargs):
    """Log when a worker is ready."""
    logger.info(f"Worker {sender.hostname} is ready.")

# Export Celery app
celery = app