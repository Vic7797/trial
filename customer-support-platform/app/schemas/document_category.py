from .base import BaseSchema, BaseCreate, BaseInDB
from uuid import UUID

class DocumentCategoryAssignmentBase(BaseSchema):
    pass

class DocumentCategoryAssignmentCreate(DocumentCategoryAssignmentBase, BaseCreate):
    document_id: UUID
    category_id: UUID

class DocumentCategoryAssignmentInDB(DocumentCategoryAssignmentBase, BaseInDB):
    document_id: UUID
    category_id: UUID

class DocumentCategoryAssignment(DocumentCategoryAssignmentInDB):
    pass