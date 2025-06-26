"""Rate limiting middleware using Redis."""
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.redis import get_redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit requests based on client IP and endpoint."""
    
    def __init__(self, app):
        super().__init__(app)
        self.redis = None
        
    async def _get_redis(self):
        """Lazy load Redis connection."""
        if not self.redis:
            self.redis = await get_redis()
        return self.redis

    async def _get_rate_limit(self, path: str) -> dict:
        """Get rate limit config for path."""
        # Default rate limits
        default = settings.RATE_LIMITS["default"]
        
        # API endpoint specific limits
        if path.startswith("/api/"):
            return settings.RATE_LIMITS["api_endpoints"]
            
        # Auth endpoints
        if path.startswith("/auth/"):
            return settings.RATE_LIMITS["auth"]
            
        return default

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host
        path = request.url.path
        
        # Get rate limit config
        limit_config = await self._get_rate_limit(path)
        max_requests = limit_config["requests"]
        window = limit_config["window_seconds"]
        
        # Generate Redis key
        key = f"rate_limit:{client_ip}:{path}"
        
        # Check rate limit
        redis = await self._get_redis()
        requests = await redis.incr(key)
        
        # Set expiry on first request
        if requests == 1:
            await redis.expire(key, window)
            
        if requests > max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "retry_after": await redis.ttl(key)
                }
            )
            
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, max_requests - requests))
        response.headers["X-RateLimit-Reset"] = str(await redis.ttl(key))
        
        return response