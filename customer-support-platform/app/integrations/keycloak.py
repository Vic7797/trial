"""Keycloak integration for authentication and authorization."""
from typing import Optional, Dict, Any
from fastapi_keycloak import FastAPIKeycloak, OIDCUser
from fastapi import HTTPException, status

from app.config import settings

# Initialize Keycloak client
keycloak_client = FastAPIKeycloak(
    server_url=settings.KEYCLOAK_BASE_URL,
    client_id=settings.KEYCLOAK_CLIENT_ID,
    client_secret=settings.KEYCLOAK_CLIENT_SECRET,
    admin_client_secret=settings.KEYCLOAK_CLIENT_SECRET,
    realm=settings.KEYCLOAK_REALM,
    callback_uri=f"{settings.SERVER_HOST}:{settings.SERVER_PORT}/auth/callback"
)

async def create_user(
    username: str,
    email: str,
    first_name: str,
    last_name: str,
    password: str,
    roles: list[str]
) -> Dict[str, Any]:
    """Create a new user in Keycloak."""
    try:
        user = await keycloak_client.create_user(
            username=username,
            email=email,
            firstName=first_name,
            lastName=last_name,
            password=password,
            roles=roles,
            sendVerificationEmail=True
        )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create user: {str(e)}"
        )

async def update_user_roles(user_id: str, roles: list[str]) -> None:
    """Update user roles in Keycloak."""
    try:
        await keycloak_client.assign_realm_roles(user_id, roles)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update user roles: {str(e)}"
        )

async def get_user_info(user_id: str) -> Dict[str, Any]:
    """Get user information from Keycloak."""
    try:
        user = await keycloak_client.get_user(user_id)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {str(e)}"
        )

async def delete_user(user_id: str) -> None:
    """Delete a user from Keycloak."""
    try:
        await keycloak_client.delete_user(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete user: {str(e)}"
        )

async def verify_token(token: str) -> Optional[OIDCUser]:
    """Verify and decode a JWT token."""
    try:
        return await keycloak_client.get_current_user(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
