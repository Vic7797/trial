from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_

from app.core.redis import Cache
from app.models.tickets import Ticket
from app.models.analytics import TicketAnalytics
from app.crud.analytics import analytics as analytics_crud


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache_prefix = "analytics:"
        self.cache_ttl = 300  # 5 minutes

    async def get_organization_stats(
        self,
        organization_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get comprehensive organization statistics."""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        cache_key = (
            f"{self.cache_prefix}org:"
            f"{organization_id}:{start_date.date()}:{end_date.date()}"
        )

        # Try cache first
        cached_stats = await Cache.get(cache_key)
        if cached_stats:
            return cached_stats

        try:
            # Gather all stats
            stats = {
                "ticket_stats": await self._get_ticket_stats(
                    organization_id,
                    start_date,
                    end_date
                ),
                "category_distribution": await self._get_category_distribution(
                    organization_id,
                    start_date,
                    end_date
                ),
                "agent_performance": await self._get_agent_performance(
                    organization_id,
                    start_date,
                    end_date
                ),
                "response_times": await self._get_response_times(
                    organization_id,
                    start_date,
                    end_date
                ),
                "customer_satisfaction": await self._get_satisfaction_stats(
                    organization_id,
                    start_date,
                    end_date
                ),
                "ticket_sources": await self._get_ticket_sources(
                    organization_id,
                    start_date,
                    end_date
                )
            }

            # Cache the results
            await Cache.set(cache_key, stats, expire=self.cache_ttl)
            return stats
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get organization stats: {str(e)}"
            )

    async def _get_ticket_stats(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get ticket-related statistics."""
        result = await analytics_crud.get_ticket_stats(
            self.db,
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "total_tickets": result["total"],
            "open_tickets": result["open"],
            "resolved_tickets": result["resolved"],
            "avg_resolution_time": result["avg_resolution_time"],
            "high_priority": result["high_priority"],
            "low_priority": result["low_priority"]
        }

    async def _get_category_distribution(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get ticket distribution across categories."""
        return await analytics_crud.get_category_distribution(
            self.db,
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )

    async def _get_agent_performance(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get performance metrics for each agent."""
        return await analytics_crud.get_agent_performance(
            self.db,
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )

    async def _get_response_times(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get response time metrics."""
        result = await analytics_crud.get_response_times(
            self.db,
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "average_first_response": result["avg_first_response"],
            "average_resolution_time": result["avg_resolution_time"],
            "within_sla": result["within_sla_percent"]
        }

    async def _get_satisfaction_stats(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get customer satisfaction metrics."""
        result = await analytics_crud.get_satisfaction_stats(
            self.db,
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "average_rating": result["avg_rating"],
            "satisfaction_rate": result["satisfaction_rate"],
            "feedback_count": result["feedback_count"]
        }

    async def _get_ticket_sources(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get distribution of tickets across different sources."""
        return await analytics_crud.get_ticket_sources(
            self.db,
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )

    async def store_ticket_analytics(
        self,
        ticket_id: UUID,
        analytics_data: Dict[str, Any]
    ) -> None:
        """Store analytics data for a resolved ticket."""
        try:
            await analytics_crud.create_ticket_analytics(
                self.db,
                ticket_id=ticket_id,
                data=analytics_data
            )

            # Invalidate relevant cache entries
            ticket = await self.db.get(Ticket, ticket_id)
            if ticket:
                cache_key = (
                    f"{self.cache_prefix}org:{ticket.organization_id}:"
                    f"{datetime.utcnow().date()}"
                )
                await Cache.delete(cache_key)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to store ticket analytics: {str(e)}"
            )

    async def get_trending_issues(
        self,
        organization_id: UUID,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get trending issues based on recent tickets."""
        cache_key = f"{self.cache_prefix}trending:{organization_id}:{days}"

        # Try cache first
        cached_trends = await Cache.get(cache_key)
        if cached_trends:
            return cached_trends

        try:
            trends = await analytics_crud.get_trending_issues(
                self.db,
                organization_id=organization_id,
                days=days
            )

            # Cache the results
            await Cache.set(cache_key, trends, expire=self.cache_ttl)
            return trends
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get trending issues: {str(e)}"
            )