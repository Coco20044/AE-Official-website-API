import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Uuid
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[uuid.UUID]=mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )
    student_id:Mapped[uuid.UUID]=mapped_column(
        Uuid,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    enrollment_id:Mapped[uuid.UUID]=mapped_column(
        Uuid,
        ForeignKey("enrollments.id"),
        nullable=False,
        index=True
    )
    amount:Mapped[int]=mapped_column(
        Integer,
        nullable=False
    )
    currency:Mapped[str]=mapped_column(
        String(30),
        nullable=False,
        index=True
    )
    status:Mapped[str]=mapped_column(
        String(30),
        default="pending", 
        nullable=False

    )
    reference:Mapped[str]=mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    paystack_access_code:Mapped[str|None]=mapped_column(
        String(500),
        nullable=True
    )
    authorization_url:Mapped[str|None]=mapped_column(
        String(500),
        nullable=True
    )
    paid_at:Mapped[datetime|None]=mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),
        default=lambda:datetime.now(timezone.utc),
        nullable=False
    )
    updated_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),
        default=lambda:datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )