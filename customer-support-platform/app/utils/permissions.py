from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from app.utils.enums import UserRole


def check_organization_access(user_org_id: UUID, target_org_id: UUID) -> bool:
    """Check if user has access to the target organization."""
    return user_org_id == target_org_id


def check_role_permissions(user_role: str, required_roles: List[str]) -> bool:
    """Check if user role has required permissions."""
    return user_role in required_roles


def validate_admin_access(user_role: str, organization_id: UUID) -> None:
    """Validate user has admin access to organization."""
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )


def validate_agent_access(user_role: str, ticket_categories: List[UUID], 
                        agent_categories: List[UUID]) -> None:
    """Validate agent has access to ticket categories."""
    if user_role != UserRole.AGENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent access required"
        )
    
    if not set(ticket_categories).issubset(set(agent_categories)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent does not have access to all ticket categories"
        )


def validate_analyst_access(user_role: str) -> None:
    """Validate user has analyst access."""
    if user_role != UserRole.ANALYST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst access required"
        )