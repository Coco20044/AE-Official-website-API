from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CohortCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    course_id: UUID
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date.")
        return self


class CohortUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    course_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None


class CohortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    course_id: UUID
    start_date: date
    end_date: date
    is_active: bool
    created_at: datetime
    updated_at: datetime
