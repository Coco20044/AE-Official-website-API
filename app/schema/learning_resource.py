from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ResourceCreate(BaseModel):
    cohort_id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    resource_url: HttpUrl
    resource_type: str = Field(min_length=1, max_length=50)


class ResourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    resource_url: HttpUrl | None = None
    resource_type: str | None = Field(
        default=None, min_length=1, max_length=50
    )
    is_active: bool | None = None


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cohort_id: UUID
    title: str
    description: str | None
    resource_url: str
    resource_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime