from typing import Optional
from pydantic import Field
from .base import BaseSchema, BaseCreate, BaseUpdate, BaseInDB
from uuid import UUID

class DocumentBase(BaseSchema):
    title: str = Field(..., max_length=255)
    content: Optional[str] = None
    file_path: Optional[str] = Field(None, max_length=500)
    file_size: Optional[int] = None
    mime_type: Optional[str] = Field(None, max_length=100)
    is_public: bool = Field(default=False)

class DocumentCreate(DocumentBase, BaseCreate):
    organization_id: UUID
    uploaded_by: Optional[UUID] = None

class DocumentUpdate(DocumentBase, BaseUpdate):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    is_public: Optional[bool] = None

class DocumentInDB(DocumentBase, BaseInDB):
    organization_id: UUID
    uploaded_by: Optional[UUID] = None

class Document(DocumentInDB):
    pass