from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.agent_category import AgentCategoryAssignment as AgentCategoryAssignmentModel
from app.schemas.agent_category import (
    AgentCategoryAssignmentCreate,
    AgentCategoryAssignmentUpdate,
)
from .base import CRUDBase


class CRUDAgentCategory(CRUDBase[
    AgentCategoryAssignmentModel,
    AgentCategoryAssignmentCreate,
    AgentCategoryAssignmentUpdate
]):
    def get_by_agent_and_category(
        self,
        db: Session,
        *,
        agent_id: str,
        category_id: str
    ) -> Optional[AgentCategoryAssignmentModel]:
        return db.query(AgentCategoryAssignmentModel).filter(
            and_(
                AgentCategoryAssignmentModel.id == agent_id,
                AgentCategoryAssignmentModel.category_id == category_id
            )
        ).first()

    def get_multi_by_agent(
        self,
        db: Session,
        *,
        agent_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentCategoryAssignmentModel]:
        return (
            db.query(AgentCategoryAssignmentModel)
            .filter(AgentCategoryAssignmentModel.id == agent_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_multi_by_category(
        self,
        db: Session,
        *,
        category_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentCategoryAssignmentModel]:
        return (
            db.query(AgentCategoryAssignmentModel)
            .filter(AgentCategoryAssignmentModel.category_id == category_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_agent_and_category(
        self,
        db: Session,
        *,
        agent_id: str,
        category_id: str
    ) -> AgentCategoryAssignmentModel:
        db_obj = AgentCategoryAssignmentModel(
            id=agent_id,
            category_id=category_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove_by_agent_and_category(
        self,
        db: Session,
        *,
        agent_id: str,
        category_id: str
    ) -> Optional[AgentCategoryAssignmentModel]:
        obj = db.query(AgentCategoryAssignmentModel).filter(
            and_(
                AgentCategoryAssignmentModel.id == agent_id,
                AgentCategoryAssignmentModel.category_id == category_id
            )
        ).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def remove_by_agent(
        self,
        db: Session,
        *,
        agent_id: str
    ) -> int:
        result = db.query(AgentCategoryAssignmentModel).filter(
            AgentCategoryAssignmentModel.id == agent_id
        ).delete()
        db.commit()
        return result

    def remove_by_category(
        self,
        db: Session,
        *,
        category_id: str
    ) -> int:
        result = db.query(AgentCategoryAssignmentModel).filter(
            AgentCategoryAssignmentModel.category_id == category_id
        ).delete()
        db.commit()
        return result


agent_category = CRUDAgentCategory(AgentCategoryAssignmentModel)
