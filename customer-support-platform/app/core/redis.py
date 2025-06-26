import json
import logging
from redis import asyncio as aioredis
from typing import Optional, Any
from fastapi import HTTPException, status
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)

# Create Redis connection pool
redis_pool = aioredis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
    max_connections=settings.REDIS_POOL_SIZE,
    timeout=settings.REDIS_POOL_TIMEOUT,
    ssl=settings.REDIS_SSL
)

# Create Redis client
redis = aioredis.Redis(connection_pool=redis_pool)


class RateLimiter:
    """Rate limiting implementation using Redis."""

    def __init__(
        self,
        key_prefix: str,
        limit: int,
        window: int
    ):
        self.key_prefix = key_prefix
        self.limit = limit
        self.window = window

    async def is_rate_limited(self, key: str) -> tuple[bool, dict]:
        """
        Check if the request should be rate limited.
        Returns (is_limited, rate_info).
        """
        redis_key = f"{self.key_prefix}:{key}"
        
        async with redis.pipeline(transaction=True) as pipe:
            now = datetime.utcnow().timestamp()
            window_start = now - self.window
            
            try:
                # Remove old requests
                await pipe.zremrangebyscore(redis_key, "-inf", window_start)
                # Count requests in current window
                await pipe.zcard(redis_key)
                # Add current request
                await pipe.zadd(redis_key, {str(now): now})
                # Set expiry
                await pipe.expire(redis_key, self.window)
                
                _, current_requests, _, _ = await pipe.execute()
                
                is_limited = current_requests >= self.limit
                reset_time = window_start + self.window
                
                rate_info = {
                    "limit": self.limit,
                    "remaining": max(0, self.limit - current_requests),
                    "reset": int(reset_time),
                }
                
                return is_limited, rate_info
                
            except Exception as e:
                # Log error here
                return False, {"error": str(e)}


class Cache:
    """Caching implementation using Redis."""
    
    @staticmethod
    async def set(
        key: str,
        value: Any,
        expire: int = 3600
    ) -> None:
        """Set a cache value with expiration."""
        try:
            await redis.set(
                key,
                json.dumps(value),
                ex=expire
            )
        except Exception as e:
            # Log error here
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cache error: {str(e)}"
            )

    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """Get a cached value."""
        try:
            data = await redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            # Log error here
            return None

    @staticmethod
    async def delete(key: str) -> bool:
        """Delete a cached value."""
        try:
            return bool(await redis.delete(key))
        except Exception as e:
            # Log error here
            return False

    @staticmethod
    async def exists(key: str) -> bool:
        """Check if a key exists."""
        try:
            return bool(await redis.exists(key))
        except Exception as e:
            # Log error here
            return False


# Token cache settings
TOKEN_CACHE_PREFIX = "token:"
TOKEN_CACHE_EXPIRE = 3600  # 1 hour


class TokenCache:
    """Token caching implementation using Redis."""

    @staticmethod
    async def cache_token(user_id: str, token_data: dict, expire: int = TOKEN_CACHE_EXPIRE) -> None:
        """Cache token data for a user."""
        key = f"{TOKEN_CACHE_PREFIX}{user_id}"
        try:
            await redis.set(
                key,
                json.dumps(token_data),
                ex=expire
            )
        except Exception as e:
            logger.error(f"Failed to cache token: {e}")
            raise

    @staticmethod
    async def get_cached_token(user_id: str) -> Optional[dict]:
        """Get cached token data for a user."""
        key = f"{TOKEN_CACHE_PREFIX}{user_id}"
        try:
            data = await redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached token: {e}")
            return None

    @staticmethod
    async def invalidate_token(user_id: str) -> None:
        """Invalidate cached token for a user."""
        key = f"{TOKEN_CACHE_PREFIX}{user_id}"
        try:
            await redis.delete(key)
        except Exception as e:
            logger.error(f"Failed to invalidate token: {e}")
            raise

    @staticmethod
    async def invalidate_all_tokens() -> None:
        """Invalidate all cached tokens."""
        try:
            keys = await redis.keys(f"{TOKEN_CACHE_PREFIX}*")
            if keys:
                await redis.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to invalidate all tokens: {e}")
            raise


# Default rate limiter instances
api_limiter = RateLimiter(
    key_prefix="api_rate",
    limit=settings.RATE_LIMITS["api_endpoints"]["requests"],
    window=settings.RATE_LIMITS["api_endpoints"]["window_seconds"]
)

auth_limiter = RateLimiter(
    key_prefix="auth_rate",
    limit=settings.RATE_LIMITS["auth"]["requests"],
    window=settings.RATE_LIMITS["auth"]["window_seconds"]
)
