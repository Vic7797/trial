from fastapi import APIRouter, Depends, Path
from app.core.security import require_admin
from app.schemas.categories import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryList
)
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=CategoryList)
async def list_categories(current_user=Depends(require_admin)):
    """List all categories (admin only)"""
    category_service = CategoryService()
    return await category_service.list_categories()


@router.post("/", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    current_user=Depends(require_admin)
):
    """Create a new category (admin only)"""
    category_service = CategoryService()
    return await category_service.create_category(category_data)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str = Path(...),
    current_user=Depends(require_admin)
):
    """Get category details (admin only)"""
    category_service = CategoryService()
    return await category_service.get_category(category_id)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_data: CategoryUpdate,
    category_id: str = Path(...),
    current_user=Depends(require_admin)
):
    """Update category (admin only)"""
    category_service = CategoryService()
    return await category_service.update_category(category_id, category_data)


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: str = Path(...),
    current_user=Depends(require_admin)
):
    """Delete category (admin only)"""
    category_service = CategoryService()
    await category_service.delete_category(category_id)
    return None


@router.post("/{category_id}/agents/{agent_id}")
async def assign_agent_to_category(
    category_id: str = Path(...),
    agent_id: str = Path(...),
    current_user=Depends(require_admin)
):
    """Assign agent to category (admin only)"""
    category_service = CategoryService()
    return await category_service.assign_agent(category_id, agent_id)


@router.delete("/{category_id}/agents/{agent_id}", status_code=204)
async def remove_agent_from_category(
    category_id: str = Path(...),
    agent_id: str = Path(...),
    current_user=Depends(require_admin)
):
    """Remove agent from category (admin only)"""
    category_service = CategoryService()
    await category_service.remove_agent(category_id, agent_id)
    return None