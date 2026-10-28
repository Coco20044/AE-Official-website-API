from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnnouncementCreate(BaseModel):
    cohort_id: UUID
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1)


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    message: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cohort_id: UUID
    title: str
    message: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
