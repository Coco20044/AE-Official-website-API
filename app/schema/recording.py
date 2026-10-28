from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class RecordingCreate(BaseModel):
    cohort_id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    recording_url: HttpUrl
    duration_minutes: int | None = Field(default=None, gt=0)


class RecordingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    recording_url: HttpUrl | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class RecordingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cohort_id: UUID
    title: str
    description: str | None
    recording_url: str
    duration_minutes: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
