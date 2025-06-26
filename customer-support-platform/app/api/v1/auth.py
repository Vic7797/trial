from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.auth import TokenResponse, RegisterRequest
from app.services.auth_service import AuthService
from app.core.security import get_current_user
from app.schemas.users import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login using username/email and password via Keycloak"""
    auth_service = AuthService()
    return await auth_service.login(form_data.username, form_data.password)

@router.post("/register", response_model=TokenResponse)
async def register(register_data: RegisterRequest):
    """Register a new organization and admin user"""
    auth_service = AuthService()
    return await auth_service.register_org_admin(register_data)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current authenticated user information"""
    return current_user

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_user = Depends(get_current_user)):
    """Logout current user from Keycloak"""
    auth_service = AuthService()
    return await auth_service.logout(current_user)