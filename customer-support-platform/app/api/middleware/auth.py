"""Authentication middleware using Keycloak."""
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.security import decode_token
from app.core.redis import get_redis
from app.services.auth_service import AuthService


class AuthMiddleware(BaseHTTPMiddleware):
    """Validate JWT tokens and handle authentication."""
    
    def __init__(self, app):
        super().__init__(app)
        self.redis = None
        self.public_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/signup",
            "/auth/refresh",
            "/healthcheck",
        }
        
    async def _get_redis(self):
        """Lazy load Redis connection."""
        if not self.redis:
            self.redis = await get_redis()
        return self.redis

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public."""
        return any(path.startswith(public) for public in self.public_paths)

    async def _validate_token(self, token: str) -> Optional[dict]:
        """Validate token and return payload if valid."""
        # Check Redis cache first
        redis = await self._get_redis()
        cached = await redis.get(f"token:{token}")
        if cached:
            return AuthService.decode_cached_token(cached)
            
        # Validate with Keycloak
        try:
            payload = await decode_token(token)
            if payload:
                # Cache successful validation
                await redis.set(
                    f"token:{token}",
                    AuthService.encode_token_for_cache(payload),
                    ex=300  # 5 minutes
                )
            return payload
        except Exception:
            return None

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        path = request.url.path
        
        # Skip auth for public paths
        if self._is_public_path(path):
            return await call_next(request)
            
        # Get token from header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing authentication token"}
            )
            
        token = auth_header.split(" ")[1]
        payload = await self._validate_token(token)
        
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"}
            )
            
        # Add user info to request state
        request.state.user = payload
        
        return await call_next(request)