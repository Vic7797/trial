from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.document import Document as DocumentModel
from app.schemas.documents import (
    DocumentCreate,
    DocumentUpdate,
)
from .base import CRUDBase


class CRUDDocument(CRUDBase[DocumentModel, DocumentCreate, DocumentUpdate]):
    def get_with_details(
        self,
        db: Session,
        *,
        document_id: str,
        organization_id: str
    ) -> Optional[DocumentModel]:
        return (
            db.query(DocumentModel)
            .filter(
                DocumentModel.id == document_id,
                DocumentModel.organization_id == organization_id
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
        is_public: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[DocumentModel]:
        query = db.query(DocumentModel).filter(
            DocumentModel.organization_id == organization_id
        )

        if is_public is not None:
            query = query.filter(DocumentModel.is_public == is_public)

        if search:
            search_filter = or_(
                DocumentModel.title.ilike(f'%{search}%'),
                DocumentModel.content.ilike(f'%{search}%')
                if DocumentModel.content else False
            )
            query = query.filter(search_filter)

        return (
            query
            .order_by(DocumentModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_multi_by_uploader(
        self,
        db: Session,
        *,
        uploaded_by: str,
        organization_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[DocumentModel]:
        return (
            db.query(DocumentModel)
            .filter(
                DocumentModel.uploaded_by == uploaded_by,
                DocumentModel.organization_id == organization_id
            )
            .order_by(DocumentModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_uploader(
        self,
        db: Session,
        *,
        obj_in: DocumentCreate,
        uploaded_by: Optional[str] = None
    ) -> DocumentModel:
        db_obj = DocumentModel(
            **obj_in.dict(exclude_unset=True),
            uploaded_by=uploaded_by
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_file_info(
        self,
        db: Session,
        *,
        db_obj: DocumentModel,
        file_path: str,
        file_size: int,
        mime_type: str
    ) -> DocumentModel:
        db_obj.file_path = file_path
        db_obj.file_size = file_size
        db_obj.mime_type = mime_type
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_content(
        self,
        db: Session,
        *,
        db_obj: DocumentModel,
        content: str
    ) -> DocumentModel:
        db_obj.content = content
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def toggle_visibility(
        self,
        db: Session,
        *,
        db_obj: DocumentModel
    ) -> DocumentModel:
        db_obj.is_public = not db_obj.is_public
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_total_size_by_organization(
        self,
        db: Session,
        *,
        organization_id: str
    ) -> int:
        result = db.query(
            db.func.coalesce(db.func.sum(DocumentModel.file_size), 0)
        ).filter(
            DocumentModel.organization_id == organization_id,
            DocumentModel.file_size.isnot(None)
        ).scalar()
        return int(result) if result is not None else 0


# Create a singleton instance
document = CRUDDocument(DocumentModel)
