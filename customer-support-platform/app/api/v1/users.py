from typing import List
from fastapi import APIRouter, Depends, Query, Path
from app.core.security import get_current_user, require_admin
from app.schemas.users import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserStatusUpdate,
    UserListResponse
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=UserListResponse)
async def list_users(
    role: str = None,
    status: str = None,
    page: int = Query(1, gt=0),
    per_page: int = Query(20, gt=0, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user = Depends(require_admin)
):
    """List all users with filters (admin only)"""
    user_service = UserService()
    return await user_service.list_users(
        role=role,
        status=status,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user = Depends(require_admin)
):
    """Create a new user (admin only)"""
    user_service = UserService()
    return await user_service.create_user(user_data)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str = Path(...),
    current_user = Depends(require_admin)
):
    """Get user details (admin only)"""
    user_service = UserService()
    return await user_service.get_user(user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_data: UserUpdate,
    user_id: str = Path(...),
    current_user = Depends(require_admin)
):
    """Update user details (admin only)"""
    user_service = UserService()
    return await user_service.update_user(user_id, user_data)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str = Path(...),
    current_user = Depends(require_admin)
):
    """Deactivate user (admin only)"""
    user_service = UserService()
    await user_service.deactivate_user(user_id)
    return None


@router.put("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    status_data: UserStatusUpdate,
    user_id: str = Path(...),
    current_user = Depends(get_current_user)
):
    """Update user's own status (active/away)"""
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Can only update own status"
        )
    
    user_service = UserService()
    return await user_service.update_status(user_id, status_data.status)