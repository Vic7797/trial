from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.category import Category as CategoryModel
from app.schemas.categories import CategoryCreate, CategoryUpdate
from .base import CRUDBase

class CRUDCategory(CRUDBase[CategoryModel, CategoryCreate, CategoryUpdate]):
    def get_by_name(
        self, 
        db: Session, 
        *, 
        name: str, 
        organization_id: str
    ) -> Optional[CategoryModel]:
        return (
            db.query(CategoryModel)
            .filter(
                CategoryModel.name == name,
                CategoryModel.organization_id == organization_id
            )
            .first()
        )
    
    def get_multi_by_organization(
        self, 
        db: Session, 
        *, 
        organization_id: str, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[CategoryModel]:
        query = db.query(CategoryModel).filter(
            CategoryModel.organization_id == organization_id
        )
        
        if is_active is not None:
            query = query.filter(CategoryModel.is_active == is_active)
        
        return (
            query
            .order_by(CategoryModel.name.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update_status(
        self, 
        db: Session, 
        *, 
        db_obj: CategoryModel, 
        is_active: bool
    ) -> CategoryModel:
        db_obj.is_active = is_active
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

category = CRUDCategory(CategoryModel)
