from typing import Optional
from fastapi_keycloak import FastAPIKeycloak, OIDCUser, UsernamePassword
from fastapi import HTTPException, status, Depends
from app.config import settings
from app.core.redis import TokenCache

import logging

logger = logging.getLogger(__name__)

# Initialize Keycloak instance
keycloak = FastAPIKeycloak(
    server_url=settings.KEYCLOAK_BASE_URL,
    client_id=settings.KEYCLOAK_CLIENT_ID,
    client_secret=settings.KEYCLOAK_CLIENT_SECRET,
    # For admin operations
    admin_client_secret=settings.KEYCLOAK_CLIENT_SECRET,
    realm=settings.KEYCLOAK_REALM,
    callback_uri=(
        f"{settings.SERVER_HOST}:{settings.SERVER_PORT}/auth/callback"
    )
)


async def get_current_user(
    token: str = Depends(keycloak.oauth2_scheme)
) -> OIDCUser:
    """Get current authenticated user from Keycloak token."""
    try:
        # Try to get user info from cache
        token_info = await TokenCache.get_cached_token(token)
        if token_info:
            return OIDCUser(**token_info)
        
        # If not in cache, validate with Keycloak
        user = await keycloak.get_current_user(token)
        
        # Cache the validated token
        await TokenCache.cache_token(
            token,
            user.model_dump(),
            expire=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return user
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: OIDCUser = Depends(get_current_user)
) -> OIDCUser:
    """Check if current user is active."""
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )
    return current_user


def has_role(required_roles: list[str]):
    """Decorator to check if user has required roles."""
    async def role_checker(
        current_user: OIDCUser = Depends(get_current_user)
    ) -> bool:
        user_roles = current_user.roles
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have required roles: {required_roles}"
            )
        return current_user
    return role_checker


async def refresh_token(refresh_token: str) -> dict:
    """Refresh an access token using a refresh token."""
    try:
        new_token = await keycloak.refresh_token(refresh_token)
        
        # Invalidate old token cache if it exists
        if new_token.get('access_token'):
            await TokenCache.invalidate_token(refresh_token)
            
            # Cache new token
            user = await keycloak.get_current_user(new_token['access_token'])
            await TokenCache.cache_token(
                new_token['access_token'],
                user.model_dump(),
                expire=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
        
        return new_token
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
