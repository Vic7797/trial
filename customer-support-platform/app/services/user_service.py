from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import json
from app.models.organization import Organization
from app.core.redis import get_redis
from app.core.security import get_password_hash
from app.crud import users as user_crud
from app.crud.organizations import organization as org_crud
from app.schemas.users import UserCreate, UserUpdate, UserResponse, UserInDB
from app.integrations.keycloak import KeycloakClient
from app.core.config import settings


class UserService:
    """Service for managing user operations with caching."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache_ttl = 3600  # 1 hour cache
        self.keycloak = KeycloakClient()

    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get user data from Redis cache."""
        redis = await get_redis()
        data = await redis.get(key)
        return json.loads(data) if data else None

    async def _set_cache(self, key: str, data: Dict[str, Any]) -> None:
        """Set user data in Redis cache."""
        redis = await get_redis()
        await redis.set(
            key,
            json.dumps(data),
            expire=self.cache_ttl
        )

    async def _invalidate_cache(self, user_id: UUID) -> None:
        """Invalidate user cache entries."""
        redis = await get_redis()
        keys = [
            f"user:{user_id}",
            f"user:email:{user_id}"
        ]
        await redis.delete(*keys)

    async def _validate_role_limits(
        self,
        org: Organization,
        role: str,
        organization_id: UUID,
        exclude_user_id: Optional[UUID] = None
    ) -> None:
        """Validate role limits against organization plan.

        Enforces a maximum of 2 admins and 2 analysts per organization.
        """
        # Get current counts for all roles we need to validate
        admin_count = await user_crud.count_by_role(
            self.db,
            organization_id,
            'admin',
            exclude_user_id=exclude_user_id
        )
        analyst_count = await user_crud.count_by_role(
            self.db,
            organization_id,
            'analyst',
            exclude_user_id=exclude_user_id
        )

        # Enforce admin/analyst/org plan limits using settings
        if role == 'admin' and admin_count >= settings.MAX_ADMINS_PER_ORG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum number of admins ({settings.MAX_ADMINS_PER_ORG}) reached for this organization."
            )
        elif role == 'analyst' and analyst_count >= settings.MAX_ANALYSTS_PER_ORG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum number of analysts ({settings.MAX_ANALYSTS_PER_ORG}) reached for this organization."
            )
        elif role == 'agent':
            agent_count = await user_crud.count_by_role(
                self.db,
                organization_id,
                'agent',
                exclude_user_id=exclude_user_id
            )
            plan_limits = settings.PLAN_LIMITS[org.plan]
            max_agents = plan_limits['max_agents']
            if agent_count >= max_agents:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum number of agents ({max_agents}) reached for your plan."
                )

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user with role validation and Keycloak integration."""
        # Check email exists
        if await user_crud.get_by_email(self.db, email=user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate organization exists
        org = await org_crud.get(self.db, id=user_data.organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Validate role limits against organization plan
        await self._validate_role_limits(
            org=org,
            role=user_data.role,
            organization_id=user_data.organization_id
        )

        # Create user in Keycloak
        keycloak_id = await self.keycloak.create_user(
            username=user_data.email,
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            password=user_data.password,
            role=user_data.role
        )

        # Create user in database
        user_in_db = UserInDB(
            **user_data.model_dump(),
            keycloak_id=keycloak_id,
            hashed_password=get_password_hash(user_data.password)
        )
        user = await user_crud.create(self.db, obj_in=user_in_db)
        
        return UserResponse.model_validate(user)

    async def get_user(self, user_id: UUID) -> Optional[UserResponse]:
        """Get user by ID with caching."""
        # Try cache first
        cached_user = await self._get_from_cache(f"user:{user_id}")
        if cached_user:
            return UserResponse(**cached_user)

        # Fallback to database
        user = await user_crud.get(self.db, id=user_id)
        if not user:
            return None

        # Cache the result
        user_data = UserResponse.model_validate(user).model_dump()
        await self._set_cache(f"user:{user_id}", user_data)
        
        return UserResponse.model_validate(user)

    async def get_by_email(self, email: str) -> Optional[UserResponse]:
        """Get user by email with caching."""
        # Try cache first
        cached_user = await self._get_from_cache(f"user:email:{email}")
        if cached_user:
            return UserResponse(**cached_user)

        # Fallback to database
        user = await user_crud.get_by_email(self.db, email=email)
        if not user:
            return None

        # Cache the result
        user_data = UserResponse.model_validate(user).model_dump()
        await self._set_cache(f"user:email:{email}", user_data)
        
        return UserResponse.model_validate(user)

    async def update_user(
        self,
        user_id: UUID,
        user_data: UserUpdate
    ) -> UserResponse:
        """Update user details with cache invalidation and role limit checks."""
        user = await user_crud.get(self.db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        
        new_role = user_data.role if user_data.role else user.role
        if new_role in ["admin", "analyst"]:
            # Only check if role is changing or user is already in that role
            if new_role != user.role or user.role in ["admin", "analyst"]:
                count = await user_crud.count_by_role(
                    self.db,
                    user.organization_id,
                    new_role,
                    exclude_user_id=user_id
                )
                if count >= 2:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Maximum number of {new_role}s reached"
                    )

        # Update in Keycloak if needed
        if any([user_data.email, user_data.first_name, user_data.last_name]):
            await self.keycloak.update_user(
                user_id=user.keycloak_id,
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name
            )

        # Update in database
        updated_user = await user_crud.update(
            self.db,
            db_obj=user,
            obj_in=user_data
        )

        # Invalidate cache
        await self._invalidate_cache(user_id)
        
        return UserResponse.model_validate(updated_user)

    async def delete_user(self, user_id: UUID) -> bool:
        """Delete user with cache invalidation."""
        user = await user_crud.get(self.db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Delete from Keycloak
        await self.keycloak.delete_user(user.keycloak_id)

        # Delete from database
        deleted = await user_crud.remove(self.db, id=user_id)

        # Invalidate cache
        await self._invalidate_cache(user_id)
        
        return deleted

    async def update_status(
        self,
        user_id: UUID,
        is_active: bool
    ) -> UserResponse:
        """Update user's active status."""
        user = await user_crud.get(self.db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update in Keycloak
        await self.keycloak.update_user_status(
            user_id=user.keycloak_id,
            is_active=is_active
        )

        # Update in database
        updated_user = await user_crud.update(
            self.db,
            db_obj=user,
            obj_in={"is_active": is_active}
        )

        # Invalidate cache
        await self._invalidate_cache(user_id)
        
        return UserResponse.model_validate(updated_user)

    async def list_users(
        self,
        organization_id: Optional[UUID] = None,
        role: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserResponse]:
        """List users with optional filtering."""
        users = await user_crud.get_multi(
            self.db,
            organization_id=organization_id,
            role=role,
            skip=skip,
            limit=limit
        )
        return [UserResponse.model_validate(user) for user in users]
