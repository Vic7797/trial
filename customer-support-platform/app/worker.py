"""Celery worker configuration and task queues setup with monitoring."""
import os
import time
import threading
from urllib.parse import quote_plus
from celery import Celery
from celery.signals import worker_ready, task_failure, task_postrun, task_prerun
from celery.app.task import Task
from celery.schedules import crontab
from kombu import Queue, Exchange

from app.config import settings
from app.core.logging import get_logger
from app.core.celery_metrics import start_celery_metrics
from app.core.celery_beat_schedule import get_beat_schedule
from prometheus_client import Counter, Histogram, Gauge
from app.integrations.sentry import init_sentry

# Initialize Sentry for Celery worker
init_sentry()

# Initialize logger
logger = get_logger(__name__)

# Log connection details for debugging
logger.info("Celery Worker Starting...")
logger.info("REDIS_HOST: %s", os.getenv('REDIS_HOST', 'not set'))
logger.info("REDIS_PORT: %s", os.getenv('REDIS_PORT', 'not set'))
logger.info("POSTGRES_HOST: %s", os.getenv('POSTGRES_HOST', 'not set'))
logger.info("POSTGRES_PORT: %s", os.getenv('POSTGRES_PORT', 'not set'))
logger.info("POSTGRES_DB: %s", os.getenv('POSTGRES_DB', 'not set'))
logger.info("SQLALCHEMY_DATABASE_URI: %s", os.getenv('SQLALCHEMY_DATABASE_URI', 'not set'))
logger.info("CELERY_BROKER_URL: %s", os.getenv('CELERY_BROKER_URL', 'not set'))
logger.info("CELERY_RESULT_BACKEND: %s", os.getenv('CELERY_RESULT_BACKEND', 'not set'))

# Ensure SQLALCHEMY_DATABASE_URI is set in the environment
if not os.getenv('SQLALCHEMY_DATABASE_URI'):
    # Construct the database URI from individual components if not set
    db_user = os.getenv('POSTGRES_USER', 'postgres')
    db_password = quote_plus(os.getenv('POSTGRES_PASSWORD', 'postgres'))
    db_host = os.getenv('POSTGRES_HOST', 'postgres')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'customer_support')
    
    db_uri = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    os.environ['SQLALCHEMY_DATABASE_URI'] = db_uri
    logger.info("Constructed SQLALCHEMY_DATABASE_URI from components")

# Prometheus metrics
TASK_START_TIME = {}

# Task metrics
TASKS_STARTED = Counter(
    'celery_tasks_started_total',
    'Total number of tasks started',
    ['task_name']
)

TASKS_COMPLETED = Counter(
    'celery_tasks_completed_total',
    'Total number of tasks completed',
    ['task_name', 'status']
)

TASK_DURATION = Histogram(
    'celery_task_duration_seconds',
    'Task execution time in seconds',
    ['task_name']
)

TASK_QUEUE_LENGTH = Gauge(
    'celery_queue_length',
    'Number of tasks in queue',
    ['queue_name']
)

# Create Celery instance
celery_app = Celery(
    'customer_support_platform',
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

# Add database_uri to the Celery config
celery_app.conf.database_uri = settings.SQLALCHEMY_DATABASE_URI

# Configure Celery
celery_app.conf.update(
    # Task Settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Queue Settings
    task_queues=(
        Queue('critical', Exchange('critical'), routing_key='critical',
              queue_arguments={'x-max-priority': 10}),
        Queue('processing', Exchange('processing'), routing_key='processing',
              queue_arguments={'x-max-priority': 10}),
        Queue('classification', Exchange('classification'),
              routing_key='classification',
              queue_arguments={'x-max-priority': 10}),
        Queue('notifications', Exchange('notifications'),
              routing_key='notifications',
              queue_arguments={'x-max-priority': 10}),
        Queue('analytics', Exchange('analytics'), routing_key='analytics',
              queue_arguments={'x-max-priority': 10}),
        Queue('polling', Exchange('polling'), routing_key='polling',
              queue_arguments={'x-max-priority': 10}),
        Queue('monitoring', Exchange('monitoring'), routing_key='monitoring',
              queue_arguments={'x-max-priority': 10}),
        Queue('default', Exchange('default'), routing_key='default',
              queue_arguments={'x-max-priority': 10})
    ),
    
    # Task Routes
    task_routes={
        'app.tasks.notification_tasks.send_critical_notification': {
            'queue': 'critical'
        },
        'app.tasks.ai_tasks.*': {
            'queue': 'processing'
        },
        'app.tasks.analytics_tasks.*': {
            'queue': 'analytics'
        },
        'app.tasks.cleanup_tasks.*': {
            'queue': 'analytics'
        },
        'app.tasks.email_tasks.*': {
            'queue': 'notifications'
        },
        'app.tasks.notification_tasks.*': {
            'queue': 'notifications'
        },
        'app.tasks.telegram_tasks.*': {
            'queue': 'notifications'
        },
        'app.tasks.monitoring_tasks.*': {
            'queue': 'monitoring'
        }
    },
    
    # Task Execution Settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.TESTING,
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=50000,  # 50MB
    
    # Result Backend Settings
    result_expires=3600,  # Results expire in 1 hour
    
    # Error Handling
    task_annotations={
        '*': {
            'rate_limit': '10/s',
            'max_retries': 3,
            'default_retry_delay': 60  # 1 minute
        }
    },
    
    # Beat Schedule
    beat_schedule=get_beat_schedule()
)

# Custom task base class
class BaseTask(Task):
    """Base task with error handling and retries."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(
            f"Task {task_id} failed: {exc}",
            exc_info=True,
            extra={
                'task_id': task_id,
                'args': args,
                'kwargs': kwargs
            }
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        logger.warning(
            f"Task {task_id} retrying: {exc}",
            extra={
                'task_id': task_id,
                'args': args,
                'kwargs': kwargs,
                'attempt': self.request.retries
            }
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)


# Set custom task base
celery_app.Task = BaseTask


@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """Record task start time and update metrics."""
    TASK_START_TIME[task_id] = time.time()
    TASKS_STARTED.labels(task_name=task.name).inc()
    logger.debug(f"Task {task.name} started", extra={"task_id": task_id})

@task_postrun.connect
def task_postrun_handler(task_id, task, *args, retval=None, state=None, **kwargs):
    """Record task completion and update metrics."""
    start_time = TASK_START_TIME.pop(task_id, None)
    if start_time:
        duration = time.time() - start_time
        TASK_DURATION.labels(task_name=task.name).observe(duration)
        logger.debug(
            f"Task {task.name} completed in {duration:.2f}s",
            extra={"task_id": task_id, "duration": duration}
        )
    
    TASKS_COMPLETED.labels(task_name=task.name, status=state).inc()

@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    """Global task failure handler."""
    logger.error(
        f"Task {sender.name} failed: {exception}",
        extra={"task_id": task_id, "task_name": sender.name, "exception": str(exception)}
    )
    TASKS_COMPLETED.labels(task_name=sender.name, status='failed').inc()


@worker_ready.connect
def worker_ready_handler(sender, **kwargs):
    """Handle worker startup."""
    logger.info(f"Worker {sender} is ready and listening to queues")


def start_metrics_server():
    """Start Prometheus metrics server in a separate thread."""
    metrics_port = int(os.getenv('CELERY_METRICS_PORT', 9809))
    start_celery_metrics(celery_app, port=metrics_port)

# Start metrics server in a separate thread
metrics_thread = threading.Thread(target=start_metrics_server, daemon=True)
metrics_thread.start()

app = celery_app
