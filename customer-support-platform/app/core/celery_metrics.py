"""Celery metrics collection for Prometheus."""
from prometheus_client import Gauge, start_http_server
from celery import Celery
import time
import logging

logger = logging.getLogger(__name__)

class CeleryMetrics:
    def __init__(self, celery_app: Celery, port: int = 9809):
        self.celery_app = celery_app
        self.port = port
        
        # Initialize metrics
        self.active_tasks = Gauge(
            'celery_active_tasks',
            'Number of active tasks',
            ['queue']
        )
        
        self.queued_tasks = Gauge(
            'celery_queued_tasks',
            'Number of tasks in queue',
            ['queue']
        )
        
        self.worker_up = Gauge(
            'celery_worker_up',
            'Celery worker status (1=up, 0=down)'
        )
        
        self.task_latency = Gauge(
            'celery_task_latency_seconds',
            'Task processing latency in seconds',
            ['task_name']
        )
    
    def collect_metrics(self):
        """Collect metrics from Celery."""
        try:
            inspector = self.celery_app.control.inspect()
            
            # Get active tasks
            active = inspector.active() or {}
            for worker, tasks in active.items():
                self.active_tasks.labels(queue=worker).set(len(tasks))
            
            # Get queued tasks
            reserved = inspector.reserved() or {}
            for worker, tasks in reserved.items():
                self.queued_tasks.labels(queue=worker).set(len(tasks))
            
            # Check worker status
            stats = inspector.stats()
            self.worker_up.set(1 if stats else 0)
            
        except Exception as e:
            logger.error(f"Error collecting Celery metrics: {e}")
            self.worker_up.set(0)
    
    def run_metrics_loop(self):
        """Start the metrics server and update loop."""
        start_http_server(self.port)
        logger.info(f"Started Celery metrics server on port {self.port}")
        
        while True:
            self.collect_metrics()
            time.sleep(15)  # Update every 15 seconds

def start_celery_metrics(celery_app: Celery, port: int = 9809):
    """Start the Celery metrics server."""
    metrics = CeleryMetrics(celery_app, port)
    metrics.run_metrics_loop()
