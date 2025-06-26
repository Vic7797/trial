from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.redis import Cache
from app.crud.categories import category as category_crud
from app.schemas.categories import CategoryCreate, CategoryUpdate
from app.models.categories import Category, UserCategoryAssignment
from app.models.tickets import Ticket


class CategoryService:
    """Service for managing categories with SLA tracking and caching."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = Cache(prefix="category")
        self.cache_timeout = 3600  # 1 hour

    async def _invalidate_cache(self, category_id: UUID = None):
        """Invalidate category cache."""
        if category_id:
            await self.cache.delete(f"cat:{category_id}")
        await self.cache.delete("cat:list")

    async def create_category(
        self,
        data: CategoryCreate,
        organization_id: UUID
    ) -> Category:
        """Create a new category."""
        try:
            # Check if category with same name exists
            existing = await category_crud.get_by_name(
                self.db,
                name=data.name,
                organization_id=organization_id
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category with this name already exists"
                )

            category = await category_crud.create(
                self.db,
                obj_in=CategoryCreate(
                    **data.dict(),
                    organization_id=organization_id
                )
            )
            await self._invalidate_cache()
            return category
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    async def get_category(self, category_id: UUID) -> Category:
        """Get category by ID with caching."""
        # Try cache
        cached = await self.cache.get(f"cat:{category_id}")
        if cached:
            return Category(**cached)

        # DB fallback
        category = await category_crud.get(self.db, id=category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

        # Cache result
        await self.cache.set(
            f"cat:{category_id}",
            category.dict(),
            timeout=self.cache_timeout
        )
        return category

    async def get_categories_by_org(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True
    ) -> List[Category]:
        """Get organization categories with caching."""
        cache_key = f"cat:org:{organization_id}"
        
        # Try cache
        cached = await self.cache.get(cache_key)
        if cached:
            categories = [Category(**cat) for cat in cached]
            if active_only:
                categories = [c for c in categories if c.is_active]
            return categories[skip:skip + limit]

        # DB fallback
        categories = await category_crud.get_multi_by_organization(
            self.db,
            organization_id=organization_id,
            is_active=active_only if active_only else None
        )

        # Cache result
        await self.cache.set(
            cache_key,
            [cat.dict() for cat in categories],
            timeout=self.cache_timeout
        )
        return categories[skip:skip + limit]

    async def update_category(
        self,
        category_id: UUID,
        data: CategoryUpdate
    ) -> Category:
        """Update category details."""
        category = await self.get_category(category_id)
        try:
            updated = await category_crud.update(
                self.db,
                db_obj=category,
                obj_in=data
            )
            await self._invalidate_cache(category_id)
            return updated
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    async def delete_category(self, category_id: UUID) -> bool:
        """Delete a category."""
        try:
            await category_crud.remove(self.db, id=category_id)
            await self._invalidate_cache(category_id)
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    async def assign_to_agent(
        self,
        category_id: UUID,
        agent_id: UUID
    ) -> Dict[str, Any]:
        """Assign category to an agent."""
        try:
            # Verify category exists
            await self.get_category(category_id)  # Will raise 404 if not found
            
            # Create assignment
            query = select(UserCategoryAssignment).where(
                and_(
                    UserCategoryAssignment.category_id == category_id,
                    UserCategoryAssignment.user_id == agent_id
                )
            )
            existing = await self.db.execute(query)
            if existing.scalar_one_or_none():
                return {"status": "already_assigned"}

            assignment = UserCategoryAssignment(
                category_id=category_id,
                user_id=agent_id
            )
            self.db.add(assignment)
            await self.db.commit()
            
            return {"status": "assigned"}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    async def remove_from_agent(
        self,
        category_id: UUID,
        agent_id: UUID
    ) -> Dict[str, Any]:
        """Remove category assignment from an agent."""
        try:
            query = select(UserCategoryAssignment).where(
                and_(
                    UserCategoryAssignment.category_id == category_id,
                    UserCategoryAssignment.user_id == agent_id
                )
            )
            result = await self.db.execute(query)
            assignment = result.scalar_one_or_none()
            
            if assignment:
                await self.db.delete(assignment)
                await self.db.commit()
                return {"status": "removed"}
            
            return {"status": "not_assigned"}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    async def get_agent_categories(
        self,
        agent_id: UUID
    ) -> List[Category]:
        """Get all categories assigned to an agent."""
        cache_key = f"cat:agent:{agent_id}"
        
        # Try cache
        cached = await self.cache.get(cache_key)
        if cached:
            return [Category(**cat) for cat in cached]

        # DB fallback
        query = select(Category).join(
            UserCategoryAssignment,
            UserCategoryAssignment.category_id == Category.id
        ).where(
            and_(
                UserCategoryAssignment.user_id == agent_id,
                Category.is_active == True  # noqa: E712
            )
        )
        result = await self.db.execute(query)
        categories = result.scalars().all()

        # Cache result
        await self.cache.set(
            cache_key,
            [cat.dict() for cat in categories],
            timeout=self.cache_timeout
        )
        return categories

    async def check_sla_breach(
        self,
        ticket_id: UUID,
        category_id: UUID
    ) -> Dict[str, Any]:
        """Check if a ticket has breached its SLA."""
        try:
            query = select(Ticket, Category).join(
                Category,
                Category.id == Ticket.category_id
            ).where(Ticket.id == ticket_id)
            
            result = await self.db.execute(query)
            ticket, category = result.one()
            
            now = datetime.utcnow()
            
            # Response SLA
            response_deadline = ticket.created_at + timedelta(
                minutes=category.response_sla_minutes
            )
            response_breached = (
                not ticket.first_response_at and
                now > response_deadline
            )
            
            # Resolution SLA
            resolution_deadline = ticket.created_at + timedelta(
                minutes=category.resolution_sla_minutes
            )
            resolution_breached = (
                not ticket.resolved_at and
                now > resolution_deadline
            )
            
            return {
                "response_sla_breached": response_breached,
                "resolution_sla_breached": resolution_breached,
                "response_deadline": response_deadline,
                "resolution_deadline": resolution_deadline
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )