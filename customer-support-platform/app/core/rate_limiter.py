"""Rate limiting utilities using Redis."""
from functools import wraps
from typing import Callable, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from app.core.redis import get_redis
from app.core.config import settings

class RateLimiter:
    """Redis-based rate limiter."""
    
    def __init__(self, redis=None):
        self.redis = redis
        
    async def init_redis(self):
        """Initialize Redis connection."""
        if not self.redis:
            self.redis = await get_redis()
    
    async def is_rate_limited(
        self,
        key: str,
        limit: int,
        window: int = 60  # in seconds
    ) -> bool:
        """Check if rate limit is exceeded."""
        await self.init_redis()
        
        current = await self.redis.get(key)
        if current and int(current) >= limit:
            return True
            
        pipe = self.redis.pipeline()
        pipe.incr(key)
        if not current:
            pipe.expire(key, window)
        await pipe.execute()
        return False

def rate_limit(
    limit: int = 100,
    window: int = 60,
    key_prefix: str = "rate_limit:",
    identifier: Optional[Callable[[Request], str]] = None
):
    """Decorator for rate limiting endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not settings.RATE_LIMIT_ENABLED:
                return await func(request, *args, **kwargs)
                
            limiter = RateLimiter()
            
            # Get client identifier (defaults to client IP)
            if identifier:
                client_id = identifier(request)
            else:
                client_id = request.client.host
                
            endpoint = request.url.path
            rate_key = f"{key_prefix}{endpoint}:{client_id}"
            
            is_limited = await limiter.is_rate_limited(rate_key, limit, window)
            if is_limited:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(window)}
                )
                
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
