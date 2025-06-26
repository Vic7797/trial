from functools import wraps
from typing import Any, Callable, Optional
import json

from app.core.redis import get_redis
from app.utils.constants import (
    USER_CACHE_TIMEOUT,
    TICKET_CACHE_TIMEOUT,
    CATEGORY_CACHE_TIMEOUT,
    DOCUMENT_CACHE_TIMEOUT
)


def cache_result(prefix: str, timeout: Optional[int] = None):
    """Decorator to cache function results in Redis."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Generate cache key from arguments
            key = f"{prefix}:{args[0] if args else ''}:{hash(str(kwargs))}"
            
            # Try to get from cache
            redis = await get_redis()
            cached = await redis.get(key)
            if cached:
                return json.loads(cached)
            
            # Get result from function
            result = await func(*args, **kwargs)
            if result:
                # Cache the result
                await redis.set(
                    key,
                    json.dumps(result),
                    ex=timeout or 3600
                )
            return result
        return wrapper
    return decorator


def invalidate_cache(prefix: str, *patterns: str):
    """Decorator to invalidate cache entries matching patterns."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            result = await func(*args, **kwargs)
            
            # Invalidate cache entries
            redis = await get_redis()
            for pattern in patterns:
                keys = await redis.keys(f"{prefix}:{pattern}")
                if keys:
                    await redis.delete(*keys)
            
            return result
        return wrapper
    return decorator


# Predefined cache decorators
cache_user = cache_result("user", USER_CACHE_TIMEOUT)
cache_ticket = cache_result("ticket", TICKET_CACHE_TIMEOUT)
cache_category = cache_result("category", CATEGORY_CACHE_TIMEOUT)
cache_document = cache_result("document", DOCUMENT_CACHE_TIMEOUT)