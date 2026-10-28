import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user, get_current_admin

from app.models.course_class import CourseClass
from app.models.cohort import Cohort
from app.models.enrollment import Enrollment
from app.models.user import User

from app.schema.course_class import (
    CourseClassCreate,
    CourseClassUpdate,
    CourseClassResponse,
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
            detail="You must be enrolled in this cohort to access its classes.",
        )

@router.post(
    "/",
    response_model=CourseClassResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_class(
    class_data: CourseClassCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    cohort = await db.get(Cohort, class_data.cohort_id)

    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort not found.",
        )

    new_class = CourseClass(
        cohort_id=class_data.cohort_id,
        title=class_data.title,
        description=class_data.description,
        scheduled_at=class_data.scheduled_at,
        duration_minutes=class_data.duration_minutes,
        meeting_url=(
            str(class_data.meeting_url)
            if class_data.meeting_url
            else None
        ),
    )

    db.add(new_class)
    await db.commit()
    await db.refresh(new_class)

    return new_class

@router.get(
    "/cohort/{cohort_id}",
    response_model=list[CourseClassResponse],
)
async def get_cohort_classes(
    cohort_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):  
    if  current_user.role!="admin":
        await check_student_enrollment(
            student_id=current_user.id,
            cohort_id=cohort_id,
            db=db,
        )

    result = await db.execute(
        select(CourseClass).where(
            CourseClass.cohort_id == cohort_id,
            CourseClass.is_active.is_(True),
        ).order_by(CourseClass.scheduled_at)
    )

    return result.scalars().all()

@router.get(
    "/{class_id}",
    response_model=CourseClassResponse,
)
async def get_class(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course_class = await db.get(CourseClass, class_id)

    if not course_class or not course_class.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found.",
        )
    if current_user.role!="admin":
        await check_student_enrollment(
            student_id=current_user.id,
            cohort_id=course_class.cohort_id,
            db=db,
        )

    return course_class



@router.patch(
    "/{class_id}",
    response_model=CourseClassResponse,
)
async def update_class(
    class_id: uuid.UUID,
    class_data: CourseClassUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    course_class = await db.get(CourseClass, class_id)

    if not course_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found.",
        )

    update_data = class_data.model_dump(exclude_unset=True)
    if "meeting_url" in update_data:
        meeting_url = update_data["meeting_url"]

        update_data["meeting_url"] = (
            str(meeting_url) if meeting_url else None
        )
    for field, value in update_data.items():
        setattr(course_class, field, value)

    await db.commit()
    await db.refresh(course_class)

    return course_class


@router.delete(
    "/{class_id}",
    status_code=status.HTTP_200_OK,
)
async def deactivate_class(
    class_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    course_class = await db.get(CourseClass, class_id)

    if not course_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found.",
        )

    course_class.is_active = False

    await db.commit()

    return {
        "message": "Class deactivated successfully."
    }

