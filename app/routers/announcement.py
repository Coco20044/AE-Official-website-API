from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user, get_current_admin
from app.models.announcement import Announcement
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schema.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
)


router = APIRouter()


async def check_student_enrollment(
    db: AsyncSession,
    student_id: UUID,
    cohort_id: UUID,
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
            detail="You must be enrolled in this cohort to view its announcements.",
        )


@router.post(
    "/",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_announcement(
    announcement_data: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    announcement = Announcement(
        cohort_id=announcement_data.cohort_id,
        title=announcement_data.title,
        message=announcement_data.message,
    )

    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)

    return announcement


@router.get(
    "/cohort/{cohort_id}",
    response_model=list[AnnouncementResponse],
)
async def get_cohort_announcements(
    cohort_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
): 
    if current_user.role!="admin":
        await check_student_enrollment(
            db=db,
            student_id=current_user.id,
            cohort_id=cohort_id,
        )

    result = await db.execute(
        select(Announcement)
        .where(
            Announcement.cohort_id == cohort_id,
            Announcement.is_active.is_(True),
        )
        .order_by(Announcement.created_at.desc())
    )

    return result.scalars().all()


@router.get(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
)
async def get_announcement(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Announcement).where(
            Announcement.id == announcement_id,
            Announcement.is_active.is_(True),
        )
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )
    if current_user.role!="admin":
        await check_student_enrollment(
            db=db,
            student_id=current_user.id,
            cohort_id=announcement.cohort_id,
        )

    return announcement


@router.patch(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
)
async def update_announcement(
    announcement_id: UUID,
    announcement_data: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Announcement).where(
            Announcement.id == announcement_id
        )
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    update_data = announcement_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(announcement, field, value)

    await db.commit()
    await db.refresh(announcement)

    return announcement


@router.delete(
    "/{announcement_id}",
    status_code=status.HTTP_200_OK,
)
async def deactivate_announcement(
    announcement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Announcement).where(
            Announcement.id == announcement_id
        )
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    announcement.is_active = False

    await db.commit()

    return {"message": "Announcement deactivated successfully."}
