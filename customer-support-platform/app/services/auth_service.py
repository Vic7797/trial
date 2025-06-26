from typing import Dict, Any
from uuid import UUID

from fastapi import HTTPException, status
from fastapi_keycloak import FastAPIKeycloak
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.redis import TokenCache
from app.crud import users as user_crud
from app.schemas.auth import TokenData
from app.schemas.users import UserCreate

class AuthService:
    """Service for authentication and org/user registration."""

    async def register_org_admin(self, register_data):
        """Register org and first admin user."""
        from app.schemas.organization import OrganizationCreate
        from app.schemas.users import UserCreate
        from app.config import settings
        from app.services.organization_service import OrganizationService
        from app.services.user_service import UserService
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.session import async_session

        org_data = OrganizationCreate(**register_data.organization)
        user_data = UserCreate(**register_data.user, role="admin")

        async with async_session() as db:
            org_service = OrganizationService(db)
            user_service = UserService(db)
            # 1. Create organization
            org = await org_service.create_organization(org_data)
            # 2. Create admin user linked to org
            tokens = await self.create_user_with_organization(user_data, org.id)
        return tokens


    def __init__(self, db: AsyncSession):
        self.db = db
        self.keycloak = FastAPIKeycloak(
            server_url=settings.KEYCLOAK_SERVER_URL,
            client_id=settings.KEYCLOAK_CLIENT_ID,
            client_secret=settings.KEYCLOAK_CLIENT_SECRET,
            admin_client_secret=settings.KEYCLOAK_ADMIN_CLIENT_SECRET,
            realm=settings.KEYCLOAK_REALM,
            callback_uri=settings.KEYCLOAK_CALLBACK_URI
        )

    async def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user with Keycloak and cache the token."""
        try:
            # Try to get cached token first
            cached_token = await TokenCache.get_cached_token(username)
            if cached_token:
                return cached_token

            # If no cached token, authenticate with Keycloak
            token_data = await self.keycloak.user_login(
                username=username,
                password=password
            )

            # Cache the token
            await TokenCache.cache_token(username, token_data)
            return token_data

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh the access token using the refresh token."""
        try:
            token_data = await self.keycloak.refresh_token(refresh_token)
            # Update cache with new token data
            user_info = await self.keycloak.get_user_info(token_data["access_token"])
            await TokenCache.cache_token(user_info["preferred_username"], token_data)
            return token_data
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token refresh failed: {str(e)}"
            )

    async def validate_token(self, token: str) -> TokenData:
        """Validate token and return user information."""
        try:
            # Decode and validate token
            token_info = await self.keycloak.decode_token(token)
            return TokenData(
                sub=token_info["sub"],
                username=token_info["preferred_username"],
                roles=token_info.get("realm_access", {}).get("roles", []),
                organization_id=token_info.get("organization_id")
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}"
            )

    async def create_user(
        self,
        user_data: UserCreate,
        organization_id: UUID,
        role: str
    ) -> Dict[str, Any]:
        """Create a user in both Keycloak and the application database."""
        try:
            # Create user in Keycloak
            keycloak_user = await self.keycloak.create_user(
                username=user_data.email,
                email=user_data.email,
                password=user_data.password,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                attributes={
                    "organization_id": str(organization_id),
                    "phone": user_data.phone
                }
            )

            # Assign role in Keycloak
            await self.keycloak.assign_realm_roles(
                user_id=keycloak_user["id"],
                roles=[role]
            )

            # Create user in application database
            db_user = await user_crud.create(
                self.db,
                obj_in=UserCreate(
                    id=keycloak_user["id"],
                    email=user_data.email,
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    phone=user_data.phone,
                    organization_id=organization_id,
                    role=role
                )
            )

            return {
                "id": db_user.id,
                "email": db_user.email,
                "role": role,
                "organization_id": organization_id
            }

        except Exception as e:
            # Cleanup if partial creation occurred
            try:
                if "keycloak_user" in locals():
                    await self.keycloak.delete_user(keycloak_user["id"])
            except:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User creation failed: {str(e)}"
            )

    async def create_user_with_organization(
        self,
        user_data: UserCreate,
        organization_id: UUID
    ) -> Dict[str, Any]:
        """
        Create a user and link to organization.
        For admin users, validates organization limits.
        Returns auth tokens.
        """
        try:
            # Verify organization exists and check role limits
            org = await org_crud.get(self.db, id=organization_id)
            if not org:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found"
                )

            # Check role limits
            if user_data.role in ['admin', 'analyst']:
                count = await user_crud.count_by_role(
                    self.db, 
                    organization_id,
                    user_data.role
                )
                if count >= 2:  # Max 2 admins/analysts
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Maximum number of {user_data.role}s reached"
                    )
            elif user_data.role == 'agent':
                # Check plan limits for agents
                agent_count = await user_crud.count_by_role(
                    self.db,
                    organization_id,
                    'agent'
                )
                plan_limits = settings.PLAN_LIMITS[org.plan]
                if agent_count >= plan_limits['max_agents']:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Maximum number of agents for plan reached"
                    )

            # Create user in Keycloak
            keycloak_user = await self.keycloak.create_user(
                username=user_data.email,
                email=user_data.email,
                password=user_data.password,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                roles=[user_data.role],
                attributes={
                    "organization_id": str(organization_id),
                    "phone": user_data.phone
                }
            )

            # Create user in database
            db_user = await user_crud.create(
                self.db,
                obj_in=UserInDB(
                    **user_data.model_dump(),
                    keycloak_id=keycloak_user["id"],
                    organization_id=organization_id
                )
            )

            # Get auth tokens
            tokens = await self.keycloak.token(
                username=user_data.email,
                password=user_data.password
            )

            return {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "token_type": "bearer",
                "expires_in": tokens["expires_in"]
            }

        except Exception as e:
            # Cleanup if partial creation occurred
            if "keycloak_user" in locals():
                await self.keycloak.delete_user(keycloak_user["id"])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    async def delete_user(self, user_id: UUID) -> bool:
        """Delete user from both Keycloak and database."""
        try:
            # Delete from Keycloak
            await self.keycloak.delete_user(str(user_id))
            # Delete from database
            await user_crud.remove(self.db, id=user_id)
            # Invalidate any cached tokens
            await TokenCache.invalidate_token(str(user_id))
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User deletion failed: {str(e)}"
            )

    async def logout(self, username: str) -> bool:
        """Logout user and invalidate tokens."""
        try:
            await TokenCache.invalidate_token(username)
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Logout failed: {str(e)}"
            )