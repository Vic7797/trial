from typing import Dict, Any, List, Optional, Union
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.core.redis import Cache
from app.core.logging import get_logger
from app.crud.organizations import organization as org_crud
from app.crud import users as user_crud
from app.models.user import User
from app.schemas.organizations import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationPlanUpdate
)
from app.services.notification_service import (
    NotificationService,
    NotificationType
)

logger = get_logger(__name__)


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_service = NotificationService(db)
        self.cache_prefix = "organization:"

    async def create_organization(
        self,
        organization_data: OrganizationCreate
    ) -> OrganizationResponse:
        """Create a new organization with free plan."""
        try:
            # Set initial plan details
            plan_details = settings.PLAN_LIMITS["free"]
            organization_data.plan = "free"
            organization_data.max_agents = plan_details["max_agents"]
            organization_data.tickets_per_month = plan_details[
                "tickets_per_month"
            ]
            organization_data.plan_expires_at = datetime.utcnow() + timedelta(
                days=30
            )

            # Create organization
            org = await org_crud.create(self.db, obj_in=organization_data)
            return org
        except Exception as e:
            import sentry_sdk
            sentry_sdk.capture_exception(e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization creation failed: {str(e)}"
            )

    async def get_organization(
        self,
        organization_id: UUID
    ) -> OrganizationResponse:
        """Get organization details with caching."""
        cache_key = f"{self.cache_prefix}{organization_id}"

        # Try cache first
        cached_org = await Cache.get(cache_key)
        if cached_org:
            return OrganizationResponse(**cached_org)

        # Cache miss, get from database
        org = await org_crud.get(self.db, id=organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Cache the result
        await Cache.set(cache_key, org.dict())
        return org

    async def _validate_plan_change(
        self,
        organization_id: UUID,
        current_plan: str,
        new_plan: str
    ) -> None:
        """
        Validate if organization can be changed to the new plan.
        
        Args:
            organization_id: The organization ID
            current_plan: Current plan name
            new_plan: New plan name to validate
            
        Raises:
            HTTPException: If plan change is not valid
        """
        if current_plan == new_plan:
            return
            
        # Get current user counts by role
        admin_count = await user_crud.count_by_role(
            self.db, 
            organization_id=organization_id,
            role='admin'
        )
        analyst_count = await user_crud.count_by_role(
            self.db,
            organization_id=organization_id,
            role='analyst'
        )
        agent_count = await user_crud.count_by_role(
            self.db,
            organization_id=organization_id,
            role='agent'
        )
        
        # Get new plan limits
        try:
            new_plan_limits = settings.PLAN_LIMITS[new_plan]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan: {new_plan}"
            )
        
        # Check if current user counts exceed new plan limits
        if admin_count > settings.MAX_ADMINS_PER_ORG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Current number of admins ({admin_count}) exceeds the maximum "
                    f"allowed ({settings.MAX_ADMINS_PER_ORG}) for any plan"
                )
            )
            
        if analyst_count > settings.MAX_ANALYSTS_PER_ORG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Current number of analysts ({analyst_count}) exceeds the maximum "
                    f"allowed ({settings.MAX_ANALYSTS_PER_ORG}) for any plan"
                )
            )
            
        max_agents = new_plan_limits.get('max_agents', 0)
        if max_agents > 0 and agent_count > max_agents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Current number of agents ({agent_count}) exceeds the maximum "
                    f"allowed ({max_agents}) for the '{new_plan}' plan. "
                    "Please remove some agents or choose a different plan."
                )
            )
    
    async def update_organization_plan(
        self,
        organization_id: UUID,
        plan_update: OrganizationPlanUpdate,
        current_user: User
    ) -> OrganizationResponse:
        """Update organization plan with validation."""
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can change organization plan"
            )
            
        org = await self.get_organization(organization_id)
        
        # Validate plan change
        await self._validate_plan_change(
            organization_id=organization_id,
            current_plan=org.plan,
            new_plan=plan_update.plan
        )
        
        # Update plan details
        plan_details = settings.PLAN_LIMITS[plan_update.plan]
        update_data = {
            'plan': plan_update.plan,
            'max_agents': plan_details['max_agents'],
            'tickets_per_month': plan_details['tickets_per_month'],
            'plan_expires_at': datetime.utcnow() + timedelta(days=30)  # 30-day billing cycle
        }
        
        updated_org = await org_crud.update(
            self.db,
            db_obj=org,
            obj_in=OrganizationUpdate(**update_data)
        )
        
        # Invalidate cache
        cache_key = f"{self.cache_prefix}{organization_id}"
        await Cache.delete(cache_key)
        
        # Log plan change
        logger.info(
            f"Organization {organization_id} plan changed from {org.plan} to {plan_update.plan}"
        )
        
        return updated_org

    async def update_organization(
        self,
        organization_id: UUID,
        organization_data: Union[OrganizationUpdate, Dict[str, Any]],
        current_user: Optional[User] = None
    ) -> OrganizationResponse:
        """Update organization details with plan change validation."""
        current_org = await self.get_organization(organization_id)
        
        # If plan is being changed, use the dedicated method
        if 'plan' in organization_data and organization_data.plan != current_org.plan:
            if not current_user or current_user.role != 'admin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admin users can change organization plan"
                )
            return await self.update_organization_plan(
                organization_id=organization_id,
                plan_update=OrganizationPlanUpdate(plan=organization_data.plan),
                current_user=current_user
            )
        
        try:
            updated_org = await org_crud.update(
                self.db,
                db_obj=current_org,
                obj_in=organization_data
            )

            # Invalidate cache
            cache_key = f"{self.cache_prefix}{organization_id}"
            await Cache.delete(cache_key)

            return updated_org
        except Exception as e:
            logger.error(f"Failed to update organization {organization_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization update failed: {str(e)}"
            )

    async def check_plan_limits(
        self,
        organization_id: UUID
    ) -> Dict[str, Any]:
        """Check organization's plan limits and usage."""
        org = await self.get_organization(organization_id)
        
        # Get current month's ticket count
        month_start = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        ticket_count = await org_crud.get_monthly_ticket_count(
            self.db,
            organization_id=organization_id,
            start_date=month_start
        )

        # Get current agent count
        agent_count = await org_crud.get_agent_count(
            self.db,
            organization_id=organization_id
        )

        # Get plan limits
        plan_limits = settings.PLAN_LIMITS[org.plan]

        return {
            "plan": org.plan,
            "expires_at": org.plan_expires_at,
            "ticket_usage": {
                "used": ticket_count,
                "limit": plan_limits["tickets_per_month"],
                "remaining": max(
                    0,
                    plan_limits["tickets_per_month"] - ticket_count
                )
            },
            "agent_usage": {
                "current": agent_count,
                "limit": plan_limits["max_agents"],
                "remaining": max(
                    0,
                    plan_limits["max_agents"] - agent_count
                )
            }
        }

    async def check_plan_expiry(self) -> None:
        """Check for expiring plans and send notifications."""
        try:
            # Get organizations with plans expiring in 7 days
            expiring_soon = await org_crud.get_expiring_plans(
                self.db,
                days_threshold=7
            )

            for org in expiring_soon:
                await self.notification_service.send_notification(
                    NotificationType.PLAN_EXPIRING,
                    org.id,
                    {
                        "plan": org.plan,
                        "expiry_date": org.plan_expires_at.strftime(
                            "%Y-%m-%d"
                        )
                    }
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Plan expiry check failed: {str(e)}"
            )

    async def get_organization_users(
        self,
        organization_id: UUID,
        role: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all users in an organization with optional role filter."""
        cache_key = (
            f"{self.cache_prefix}users:{organization_id}"
            f":{role if role else 'all'}"
        )

        # Try cache first
        cached_users = await Cache.get(cache_key)
        if cached_users:
            return cached_users

        try:
            users = await org_crud.get_organization_users(
                self.db,
                organization_id=organization_id,
                role=role
            )

            # Transform and cache
            user_list = [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "role": u.role,
                    "active": u.active
                }
                for u in users
            ]

            await Cache.set(cache_key, user_list, expire=300)  # Cache for 5 mins
            return user_list
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get organization users: {str(e)}"
            )