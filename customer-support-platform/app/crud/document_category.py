 from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.document_category import DocumentCategoryAssignment as DocumentCategoryAssignmentModel
from app.schemas.document_category import (
    DocumentCategoryAssignmentCreate,
    DocumentCategoryAssignmentUpdate,
)
from .base import CRUDBase


class CRUDDocumentCategory(CRUDBase[
    DocumentCategoryAssignmentModel,
    DocumentCategoryAssignmentCreate,
    DocumentCategoryAssignmentUpdate
]):
    def get_by_document_and_category(
        self,
        db: Session,
        *,
        document_id: str,
        category_id: str
    ) -> Optional[DocumentCategoryAssignmentModel]:
        return db.query(DocumentCategoryAssignmentModel).filter(
            and_(
                DocumentCategoryAssignmentModel.document_id == document_id,
                DocumentCategoryAssignmentModel.category_id == category_id
            )
        ).first()

    def get_multi_by_document(
        self,
        db: Session,
        *,
        document_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[DocumentCategoryAssignmentModel]:
        return (
            db.query(DocumentCategoryAssignmentModel)
            .filter(DocumentCategoryAssignmentModel.document_id == document_id)
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
    ) -> List[DocumentCategoryAssignmentModel]:
        return (
            db.query(DocumentCategoryAssignmentModel)
            .filter(DocumentCategoryAssignmentModel.category_id == category_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_document_and_category(
        self,
        db: Session,
        *,
        document_id: str,
        category_id: str
    ) -> DocumentCategoryAssignmentModel:
        db_obj = DocumentCategoryAssignmentModel(
            document_id=document_id,
            category_id=category_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove_by_document_and_category(
        self,
        db: Session,
        *,
        document_id: str,
        category_id: str
    ) -> Optional[DocumentCategoryAssignmentModel]:
        obj = db.query(DocumentCategoryAssignmentModel).filter(
            and_(
                DocumentCategoryAssignmentModel.document_id == document_id,
                DocumentCategoryAssignmentModel.category_id == category_id
            )
        ).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def remove_by_document(
        self,
        db: Session,
        *,
        document_id: str
    ) -> int:
        result = db.query(DocumentCategoryAssignmentModel).filter(
            DocumentCategoryAssignmentModel.document_id == document_id
        ).delete()
        db.commit()
        return result

    def remove_by_category(
        self,
        db: Session,
        *,
        category_id: str
    ) -> int:
        result = db.query(DocumentCategoryAssignmentModel).filter(
            DocumentCategoryAssignmentModel.category_id == category_id
        ).delete()
        db.commit()
        return result


document_category = CRUDDocumentCategory(DocumentCategoryAssignmentModel)
