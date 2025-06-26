from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.core.security import require_admin_or_analyst
from app.schemas.analytics import (
    TicketSummary,
    CategoryDistribution,
    CriticalityDistribution,
    AgentPerformance,
    ResponseTimes,
    ResolutionRates
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/tickets/summary", response_model=TicketSummary)
async def get_ticket_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_id: Optional[str] = None,
    current_user=Depends(require_admin_or_analyst)
):
    """Get overall ticket statistics"""
    analytics_service = AnalyticsService()
    return await analytics_service.get_ticket_summary(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id
    )


@router.get("/tickets/by-category", response_model=CategoryDistribution)
async def get_tickets_by_category(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user=Depends(require_admin_or_analyst)
):
    """Get ticket distribution by category"""
    analytics_service = AnalyticsService()
    return await analytics_service.get_category_distribution(
        start_date=start_date,
        end_date=end_date
    )


@router.get("/tickets/by-criticality", response_model=CriticalityDistribution)
async def get_tickets_by_criticality(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_id: Optional[str] = None,
    current_user=Depends(require_admin_or_analyst)
):
    """Get ticket distribution by criticality"""
    analytics_service = AnalyticsService()
    return await analytics_service.get_criticality_distribution(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id
    )


@router.get("/agents/performance", response_model=list[AgentPerformance])
async def get_agent_performance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    agent_id: Optional[str] = None,
    category_id: Optional[str] = None,
    current_user=Depends(require_admin_or_analyst)
):
    """Get agent performance metrics"""
    analytics_service = AnalyticsService()
    return await analytics_service.get_agent_performance(
        start_date=start_date,
        end_date=end_date,
        agent_id=agent_id,
        category_id=category_id
    )


@router.get("/response-times", response_model=ResponseTimes)
async def get_response_times(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    current_user=Depends(require_admin_or_analyst)
):
    """Get average response times"""
    analytics_service = AnalyticsService()
    return await analytics_service.get_response_times(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        agent_id=agent_id
    )


@router.get("/resolution-rates", response_model=ResolutionRates)
async def get_resolution_rates(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    current_user=Depends(require_admin_or_analyst)
):
    """Get resolution rate metrics"""
    analytics_service = AnalyticsService()
    return await analytics_service.get_resolution_rates(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        agent_id=agent_id
    )