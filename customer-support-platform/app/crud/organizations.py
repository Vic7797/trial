from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.organization import Organization as OrganizationModel
from app.schemas.organizations import OrganizationCreate, OrganizationUpdate
from .base import CRUDBase

class CRUDOrganization(CRUDBase[OrganizationModel, OrganizationCreate, OrganizationUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[OrganizationModel]:
        return db.query(OrganizationModel).filter(OrganizationModel.name == name).first()
    
    def get_multi_active(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[OrganizationModel]:
        return (
            db.query(OrganizationModel)
            .filter(OrganizationModel.is_active == True)  # noqa: E712
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update_status(
        self, db: Session, *, db_obj: OrganizationModel, is_active: bool
    ) -> OrganizationModel:
        db_obj.is_active = is_active
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

organization = CRUDOrganization(OrganizationModel)
