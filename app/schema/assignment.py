from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

class AssignmentCreate(BaseModel):
    cohort_id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    instructions: str | None = None
    attachment_url: HttpUrl | None = None
    deadline: datetime | None = None

class AssignmentUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    description: str | None = Field(
        default=None,
        min_length=1,
    )
    instructions: str | None = None
    attachment_url: HttpUrl | None = None
    deadline: datetime | None = None
    is_active: bool | None = None

class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cohort_id: UUID
    title: str
    description: str
    instructions: str | None
    attachment_url: str | None
    deadline: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
