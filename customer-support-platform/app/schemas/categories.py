from pydantic import Field
from .base import BaseSchema, BaseCreate, BaseUpdate, BaseInDB
from uuid import UUID

class CategoryBase(BaseSchema):
    name: str = Field(..., max_length=255)
    description: str
    is_active: bool = Field(default=True)
    color: str = Field(..., max_length=7)

class CategoryCreate(CategoryBase, BaseCreate):
    organization_id: UUID

class CategoryUpdate(CategoryBase, BaseUpdate):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    color: Optional[str] = Field(None, max_length=7)

class CategoryInDB(CategoryBase, BaseInDB):
    organization_id: UUID

class Category(CategoryInDB):
    pass