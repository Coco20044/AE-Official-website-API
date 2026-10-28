from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class SubmissionCreate(BaseModel):

    assignment_id: UUID
    content: str | None = None
    submission_url: HttpUrl | None = None

    @model_validator(mode="after")
    def validate_submission_content(self):
        if not self.content or not self.content.strip():
            if not self.submission_url:
                raise ValueError(
                    "Provide written content, a submission URL, or both."
                )

        return self


class SubmissionUpdate(BaseModel):
    content: str | None = None
    submission_url: HttpUrl | None = None
    
    @model_validator(mode="after")
    def validate_submission_update(self):
        if (
            "content" not in self.model_fields_set
            and "submission_url" not in self.model_fields_set
        ):
            raise ValueError(
                "Provide at least one field to update."
            )

        if (
            self.content is not None
            and not self.content.strip()
            and self.submission_url is None
        ):
            raise ValueError(
                "Provide written content, a submission URL, or both."
            )

        return self


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    assignment_id: UUID
    student_id: UUID
    content: str | None
    submission_url: str | None
    submitted_at: datetime
    updated_at: datetime
