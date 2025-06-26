from .base import BaseSchema, BaseCreate, BaseInDB
from uuid import UUID

class AgentCategoryAssignmentBase(BaseSchema):
    pass

class AgentCategoryAssignmentCreate(AgentCategoryAssignmentBase, BaseCreate):
    id: UUID
    category_id: UUID

class AgentCategoryAssignmentInDB(AgentCategoryAssignmentBase, BaseInDB):
    id: UUID
    category_id: UUID

class AgentCategoryAssignment(AgentCategoryAssignmentInDB):
    pass