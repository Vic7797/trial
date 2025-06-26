from datetime import datetime
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field
from uuid import UUID

# Generic Type Vars
T = TypeVar('T')

class BaseSchema(BaseModel):
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }

class BaseCreate(BaseSchema):
    pass

class BaseUpdate(BaseSchema):
    pass

class BaseInDB(BaseSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime