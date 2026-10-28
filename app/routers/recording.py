import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user, get_current_admin

from app.models.recording import Recording
from app.models.cohort import Cohort
from app.models.enrollment import Enrollment
from app.models.user import User

from app.schema.recording import (
    RecordingCreate,
    RecordingUpdate,
    RecordingResponse,
)


router = APIRouter()


async def check_student_enrollment(
    student_id: uuid.UUID,
    cohort_id: uuid.UUID,
    db: AsyncSession,
):
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.cohort_id == cohort_id,
            Enrollment.status == "enrolled",
        )
    )

    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be enrolled in this cohort to access its recordings.",
        )


@router.post(
    "/",
    response_model=RecordingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recording(
    recording_data: RecordingCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    cohort = await db.get(Cohort, recording_data.cohort_id)

    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort not found.",
        )

    new_recording = Recording(
        cohort_id=recording_data.cohort_id,
        title=recording_data.title,
        description=recording_data.description,
        recording_url=str(recording_data.recording_url),
        duration_minutes=recording_data.duration_minutes,
    )

    db.add(new_recording)
    await db.commit()
    await db.refresh(new_recording)

    return new_recording


@router.get(
    "/cohort/{cohort_id}",
    response_model=list[RecordingResponse],
)
async def get_cohort_recordings(
    cohort_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cohort = await db.get(Cohort, cohort_id)

    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort not found.",
        )
    if current_user.role!="admin": 
        await check_student_enrollment(
            student_id=current_user.id,
            cohort_id=cohort_id,
            db=db,
        )

    result = await db.execute(
        select(Recording)
        .where(
            Recording.cohort_id == cohort_id,
            Recording.is_active.is_(True),
        )
        .order_by(Recording.created_at.desc())
    )

    return result.scalars().all()


@router.get(
    "/{recording_id}",
    response_model=RecordingResponse,
)
async def get_recording(
    recording_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = await db.get(Recording, recording_id)

    if not recording or not recording.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found.",
        )
    if current_user.role!="admin": 
        await check_student_enrollment(
            student_id=current_user.id,
            cohort_id=recording.cohort_id,
            db=db,
        )

    return recording


@router.patch(
    "/{recording_id}",
    response_model=RecordingResponse,
)
async def update_recording(
    recording_id: uuid.UUID,
    recording_data: RecordingUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    recording = await db.get(Recording, recording_id)

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found.",
        )

    update_data = recording_data.model_dump(exclude_unset=True)

    if "recording_url" in update_data:
        recording_url = update_data["recording_url"]

        update_data["recording_url"] = (
            str(recording_url) if recording_url else None
        )

    for field, value in update_data.items():
        setattr(recording, field, value)

    await db.commit()
    await db.refresh(recording)

    return recording


@router.delete(
    "/{recording_id}",
    status_code=status.HTTP_200_OK,
)
async def deactivate_recording(
    recording_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    recording = await db.get(Recording, recording_id)

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found.",
        )

    recording.is_active = False

    await db.commit()

    return {
        "message": "Recording deactivated successfully."
    }
