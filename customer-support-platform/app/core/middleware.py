"""Core middleware functionality."""
from typing import Callable, Dict, Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import logger


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )

    # Request ID
    app.add_middleware(RequestIDMiddleware)
    
    # Rate Limiting
    app.add_middleware(RateLimitMiddleware)
    
    # Authentication
    app.add_middleware(AuthMiddleware)
    
    # Request Logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # Error Handling
    app.add_middleware(ErrorHandlingMiddleware)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request."""
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(
                "Unhandled error",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "path": request.url.path,
                    "method": request.method,
                }
            )
            
            # Send to Sentry if configured
            if settings.SENTRY_DSN:
                import sentry_sdk
                sentry_sdk.capture_exception(e)
            
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": getattr(request.state, "request_id", None)
                }
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request and response details."""
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Log request details
        logger.info(
            "Request processed",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.url.path,
                "duration": duration,
                "status_code": response.status_code,
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        return response