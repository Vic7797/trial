"""Validators for various business rules and constraints."""
from typing import Optional
from fastapi import HTTPException, status
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_file_size(size: int, max_size: Optional[int] = None) -> bool:
    """Validate file size against maximum allowed size.

    Args:
        size: File size in bytes
        max_size: Optional override for max size in bytes

    Returns:
        bool: True if file size is within limits, False otherwise
    """
    try:
        max_allowed = max_size or settings.MAX_FILE_SIZE
        if max_allowed <= 0:  # Unlimited
            return True
        return size <= max_allowed
    except (TypeError, ValueError) as e:
        logger.error("Invalid file size validation: %s", e)
        return False


def validate_mime_type(
    mime_type: str,
    allowed_types: Optional[list[str]] = None,
) -> bool:
    """Validate file mime type against allowed types."""
    allowed = allowed_types or settings.ALLOWED_MIME_TYPES
    return mime_type in allowed


def validate_agent_limit(current_count: int, plan: str) -> bool:
    """Validate agent count against plan limits.

    Args:
        current_count: Current number of agents
        plan: Plan name to validate against

    Returns:
        bool: True if within limits, False if exceeded
    """
    plan_limits = settings.PLAN_LIMITS.get(plan)
    if not plan_limits:
        logger.error("Invalid plan specified: %s", plan)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan: {plan}"
        )

    max_agents = plan_limits.get('max_agents', 0)
    if max_agents == -1:  # Unlimited
        return True

    if current_count >= max_agents:
        msg = (
            f"Agent limit of {max_agents} reached for plan '{plan}'. "
            "Please upgrade your plan to add more agents."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    return True


def validate_ticket_limit(current_count: int, plan: str) -> bool:
    """Validate monthly ticket count against plan limits.

    Args:
        current_count: Current number of tickets this month
        plan: Plan name to validate against

    Returns:
        bool: True if within limits, False if exceeded

    Raises:
        HTTPException: If plan is invalid or limit exceeded
    """
    plan_limits = settings.PLAN_LIMITS.get(plan)
    if not plan_limits:
        logger.error("Invalid plan specified: %s", plan)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan: {plan}"
        )

    max_tickets = plan_limits.get('tickets_per_month', 0)
    if max_tickets == -1:  # Unlimited
        return True

    if current_count >= max_tickets:
        msg = (
            f"Ticket limit of {max_tickets} per month reached "
            f"for plan '{plan}'. Please upgrade your plan or "
            "wait until next month."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    return True


def validate_storage_limit(current_size: int, plan: str) -> bool:
    """Validate storage usage against plan limits.

    Args:
        current_size: Current storage usage in bytes
        plan: Plan name to validate against

    Returns:
        bool: True if within limits, False if exceeded

    Raises:
        HTTPException: If plan is invalid
    """
    plan_limits = settings.PLAN_LIMITS.get(plan)
    if not plan_limits:
        logger.error("Invalid plan specified: %s", plan)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan: {plan}"
        )

    max_storage = plan_limits.get('storage_limit', 0)
    if max_storage == -1:  # Unlimited
        return True

    if current_size >= max_storage:
        error_msg = (
            f"Storage limit of {max_storage} bytes reached for plan '{plan}'. "
            "Please upgrade your plan or free up some space."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    return True