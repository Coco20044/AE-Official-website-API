from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EnrollmentCreate(BaseModel):
    cohort_id: UUID


class AdminEnrollmentCreate(BaseModel):
    student_id: UUID
    cohort_id: UUID


class EnrollmentUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        allowed_statuses = {"enrolled", "completed", "withdrawn"}

        if value not in allowed_statuses:
            raise ValueError(
                "Status must be enrolled, completed, or withdrawn."
            )

        return value


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    cohort_id: UUID
    status: str
    enrolled_at: datetime
    created_at: datetime
    updated_at: datetime
