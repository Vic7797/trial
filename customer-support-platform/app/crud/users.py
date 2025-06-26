from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.user import User as UserModel
from app.schemas.users import UserCreate, UserUpdate
from .base import CRUDBase

class CRUDUser(CRUDBase[UserModel, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[UserModel]:
        return db.query(UserModel).filter(UserModel.email == email).first()
    
    def get_by_keycloak_id(self, db: Session, *, keycloak_user_id: str) -> Optional[UserModel]:
        return db.query(UserModel).filter(UserModel.keycloak_user_id == keycloak_user_id).first()
    
    def get_multi_by_organization(
        self, db: Session, *, organization_id: str, skip: int = 0, limit: int = 100
    ) -> List[UserModel]:
        return (
            db.query(UserModel)
            .filter(UserModel.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_multi_active_agents(
        self, db: Session, *, organization_id: str, skip: int = 0, limit: int = 100
    ) -> List[UserModel]:
        return (
            db.query(UserModel)
            .filter(
                UserModel.organization_id == organization_id,
                UserModel.role == 'agent',
                UserModel.is_active == True,  # noqa: E712
                UserModel.status == 'active'
            )
            .order_by(UserModel.last_assigned_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update_last_assigned(self, db: Session, *, db_obj: UserModel) -> UserModel:
        from sqlalchemy import func
        db_obj.last_assigned_at = func.now()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
        
    def count_by_role(
        self, 
        db: Session, 
        organization_id: str, 
        role: str,
        exclude_user_id: Optional[str] = None
    ) -> int:
        """
        Count users by role in an organization, optionally excluding a user.
        
        Args:
            db: Database session
            organization_id: Organization ID to filter by
            role: Role to filter by
            exclude_user_id: Optional user ID to exclude from count
            
        Returns:
            int: Count of users matching the criteria
        """
        query = db.query(UserModel).filter(
            UserModel.organization_id == organization_id,
            UserModel.role == role,
            UserModel.is_active == True  # noqa: E712
        )
        
        if exclude_user_id:
            query = query.filter(UserModel.id != exclude_user_id)
            
        return query.count()

user = CRUDUser(UserModel)
