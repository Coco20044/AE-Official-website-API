from datetime import datetime
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class CourseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    price:Decimal=Field(
        gt=0,
        max_digits=12,
        decimal_places=2
    )


class CourseUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    description: str | None = None
    price:Decimal|None=Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2
    )
    is_active: bool | None = None


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    price:Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
