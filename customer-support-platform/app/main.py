from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.config import settings
from app.core.database import get_db
from app.core.metrics import setup_metrics
from app.core.logging import get_logger
from app.integrations.sentry import init_sentry
from app.integrations.keycloak import KeycloakClient
from app.integrations.razorpay import RazorpayClient
from app.api.v1 import router as api_router
import redis
import pika

logger = get_logger(__name__)

# Initialize Sentry at startup
init_sentry()

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )
    
    # Setup Prometheus metrics
    setup_metrics(app)
    
    # Include API v1 router
    app.include_router(api_router)
    
    return app

app = create_application()

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}

@app.get("/health/db")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """Database health check endpoint."""
    try:
        # Test DB connection
        await db.execute("SELECT 1")
        return {"database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )

@app.get("/health/keycloak")
async def keycloak_health_check():
    try:
        kc = KeycloakClient()
        # Try to get the server info or realm info
        info = kc.admin.get_server_info()
        return {"keycloak": "connected", "info": info}
    except Exception as e:
        logger.error(f"Keycloak health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Keycloak connection failed")

@app.get("/health/razorpay")
async def razorpay_health_check():
    try:
        client = RazorpayClient()
        # Try to fetch something simple (e.g. plans)
        plans = client.client.plan.all({'count': 1})
        return {"razorpay": "connected", "plans": plans.get('items', [])}
    except Exception as e:
        logger.error(f"Razorpay health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Razorpay connection failed")

@app.get("/health/redis")
async def redis_health_check():
    try:
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        pong = r.ping()
        return {"redis": "connected", "pong": pong}
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Redis connection failed")

@app.get("/health/rabbitmq")
async def rabbitmq_health_check():
    try:
        params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT)
        conn = pika.BlockingConnection(params)
        conn.close()
        return {"rabbitmq": "connected"}
    except Exception as e:
        logger.error(f"RabbitMQ health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="RabbitMQ connection failed")

@app.get("/health/sentry")
async def sentry_health_check():
    try:
        if settings.SENTRY_DSN:
            return {"sentry": "configured"}
        else:
            return {"sentry": "not_configured"}
    except Exception as e:
        logger.error(f"Sentry health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Sentry config check failed")

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with basic API information."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV,
        "documentation": "/api/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.SERVER_HOST, 
        port=settings.SERVER_PORT, 
        workers=settings.WORKERS_COUNT, 
        reload=settings.RELOAD
    )