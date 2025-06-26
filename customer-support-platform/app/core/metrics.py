"""Prometheus metrics configuration for the application."""
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
from fastapi import FastAPI
import time

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

# Custom application metrics
TICKET_CREATED = Counter(
    'tickets_created_total',
    'Total number of tickets created',
    ['category', 'priority']
)

TICKET_RESOLVED = Counter(
    'tickets_resolved_total',
    'Total number of tickets resolved',
    ['category', 'priority']
)

ACTIVE_USERS = Gauge(
    'active_users',
    'Number of active users in the system'
)

def setup_metrics(app: FastAPI) -> None:
    """Configure Prometheus metrics for the FastAPI app."""
    Instrumentator().instrument(app).expose(app)
    
    @app.middleware("http")
    async def add_process_time_header(request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Record request metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(process_time)
        
        return response
