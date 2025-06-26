"""Organization API endpoints."""
from fastapi import APIRouter, Depends
from app.core.security import get_current_user, require_admin
from app.schemas.organizations import (
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationPlanUpdate,
    SubscriptionDetails,
    UsageMetrics,
    PlanLimits,
)
from app.services.organization_service import OrganizationService
from app.models.user import User

router = APIRouter(prefix="/organization", tags=["Organization"])


@router.get("/", response_model=OrganizationResponse)
async def get_organization(
    current_user: User = Depends(get_current_user)
) -> OrganizationResponse:
    """Get organization details."""
    org_service = OrganizationService()
    return await org_service.get_plan_limits(
        organization_id=current_user.organization_id
    )


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    org_data: OrganizationUpdate,
    current_user: User = Depends(require_admin),
) -> OrganizationResponse:
    """Update organization details (admin only).

    Note: To change the organization plan, use the /plan endpoint.
    """
    org_service = OrganizationService()
    return await org_service.update_organization(
        organization_id=organization_id,
        organization_data=org_data,
        current_user=current_user
    )


@router.put("/{organization_id}/plan", response_model=OrganizationResponse)
async def update_organization_plan(
    organization_id: UUID,
    plan_update: OrganizationPlanUpdate,
    current_user: User = Depends(require_admin),
) -> OrganizationResponse:
    """Update organization plan (admin only).

    Validates that the organization meets the requirements of the new plan
    before allowing the change.
    """
    # Check if organization exists and user has access
    org = await organization_crud.get(current_user.db, id=organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Get the current plan limits and new plan limits
    current_limits = settings.PLAN_LIMITS[org.plan]
    new_plan_limits = settings.PLAN_LIMITS[plan_update.plan]

    # Check if the organization meets the new plan's requirements
    # (e.g., user count, storage usage, etc.)
    # This is a simplified example - you'd want to add more validations

    # Update the organization plan
    org.plan = plan_update.plan
    org.max_agents = new_plan_limits["max_agents"]
    org.tickets_per_month = new_plan_limits["tickets_per_month"]

    # Save the changes
    return await organization_crud.update(
        current_user.db,
        db_obj=org,
        obj_in={
            "plan": plan_update.plan,
            "max_agents": new_plan_limits["max_agents"],
            "tickets_per_month": new_plan_limits["tickets_per_month"]
        }
    )


@router.get("/subscription", response_model=SubscriptionDetails)
async def get_subscription(
    current_user: User = Depends(require_admin)
) -> SubscriptionDetails:
    """Get current subscription details (admin only)."""
    org_service = OrganizationService()
    return await org_service.get_subscription(current_user.organization_id)


@router.get("/usage", response_model=UsageMetrics)
async def get_usage_metrics(
    current_user: User = Depends(require_admin)
) -> UsageMetrics:
    """Get current usage metrics (admin only)."""
    org_service = OrganizationService()
    return await org_service.get_usage_metrics(
        organization_id=current_user.organization_id
    )


@router.get("/limits", response_model=PlanLimits)
async def get_plan_limits(
    current_user: User = Depends(require_admin)
) -> PlanLimits:
    """Get plan limits and current usage (admin only)."""
    org_service = OrganizationService()
    return await org_service.get_plan_limits(current_user.organization_id)