from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

class CourseClassCreate(BaseModel):
    cohort_id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    meeting_url: HttpUrl | None = None

class CourseClassUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    meeting_url: HttpUrl | None = None
    is_active: bool | None = None

class CourseClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cohort_id: UUID
    title: str
    description: str | None
    scheduled_at: datetime | None
    duration_minutes: int | None
    meeting_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
