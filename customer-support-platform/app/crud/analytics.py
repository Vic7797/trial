from typing import Optional, List, Dict, Any
from datetime import date, datetime
from uuid import UUID
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analytics import TicketAnalytics
from app.schemas.analytics import TicketAnalyticsCreate, TicketAnalyticsUpdate
from app.crud.base import CRUDBase


class CRUDAnalytics(CRUDBase[TicketAnalytics, TicketAnalyticsCreate, TicketAnalyticsUpdate]):
    async def get_by_organization_and_date(
        self, 
        db: AsyncSession, 
        organization_id: UUID, 
        date: date
    ) -> Optional[TicketAnalytics]:
        result = await db.execute(
            select(TicketAnalytics)
            .where(
                TicketAnalytics.organization_id == organization_id,
                TicketAnalytics.date == date
            )
        )
        return result.scalars().first()

    async def get_metrics_in_date_range(
        self,
        db: AsyncSession,
        organization_id: UUID,
        start_date: date,
        end_date: date,
        category_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None
    ) -> List[TicketAnalytics]:
        query = select(TicketAnalytics).where(
            TicketAnalytics.organization_id == organization_id,
            TicketAnalytics.date >= start_date,
            TicketAnalytics.date <= end_date
        )
        
        if category_id:
            query = query.where(TicketAnalytics.category_id == category_id)
        if agent_id:
            query = query.where(TicketAnalytics.agent_id == agent_id)
            
        result = await db.execute(query)
        return result.scalars().all()

    async def get_aggregated_metrics(
        self,
        db: AsyncSession,
        organization_id: UUID,
        start_date: date,
        end_date: date,
        group_by: List[str] = None
    ) -> List[Dict[str, Any]]:
        if not group_by:
            group_by = []
            
        select_fields = [
            func.sum(TicketAnalytics.total_tickets).label("total_tickets"),
            func.sum(TicketAnalytics.resolved_tickets).label("resolved_tickets"),
            func.avg(TicketAnalytics.avg_resolution_time_hours).label("avg_resolution_time_hours")
        ]
        
        group_by_fields = []
        for field in group_by:
            if hasattr(TicketAnalytics, field):
                select_fields.append(getattr(TicketAnalytics, field))
                group_by_fields.append(getattr(TicketAnalytics, field))
        
        query = select(*select_fields).where(
            TicketAnalytics.organization_id == organization_id,
            TicketAnalytics.date >= start_date,
            TicketAnalytics.date <= end_date
        )
        
        if group_by_fields:
            query = query.group_by(*group_by_fields)
            
        result = await db.execute(query)
        return [dict(row) for row in result.all()]


analytics = CRUDAnalytics(TicketAnalytics)