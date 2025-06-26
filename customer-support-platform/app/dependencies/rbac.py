from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.user import User
from app.crud.users import user_crud
from app.core.security import decode_jwt
from typing import List

class RoleGuard:
    """Role-based access dependency for FastAPI routes."""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        token = credentials.credentials
        payload = decode_jwt(token)
        user_id = payload.get('sub')
        user = user_crud.get_by_id(user_id)
        if not user or user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
