from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status,Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.limiter import limiter
from app.database.session import get_db
from app.dependencies.auth import get_current_admin
from app.models.course import Course
from app.models.user import User
from app.schema.course import CourseCreate, CourseUpdate, CourseResponse


router = APIRouter()


@router.post(
    "/",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def create_course(
    request: Request,
    course_data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    course = Course(
        name=course_data.name,
        description=course_data.description,
        price=course_data.price
    )

    db.add(course)

    try:
        await db.commit()
        await db.refresh(course)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A course with this name already exists.",
        )

    return course


@router.get(
    "/",
    response_model=list[CourseResponse],
)
@limiter.limit("30/minute")
async def get_courses(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Course)
        .where(Course.is_active.is_(True))
        .order_by(Course.name)
    )

    return result.scalars().all()


@router.get(
    "/{course_id}",
    response_model=CourseResponse,
)
@limiter.limit("30/minute")
async def get_course(
    request: Request,
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Course).where(
            Course.id == course_id,
            Course.is_active.is_(True),
        )
    )

    course = result.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )

    return course


@router.patch(
    "/{course_id}",
    response_model=CourseResponse,
)
@limiter.limit("10/minute")
async def update_course(
    request: Request,
    course_id: UUID,
    course_data: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Course).where(Course.id == course_id)
    )

    course = result.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )

    updates = course_data.model_dump(exclude_unset=True)

    if "name" in updates and updates["name"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Course name cannot be null.",
        )

    for field, value in updates.items():
        setattr(course, field, value)

    try:
        await db.commit()
        await db.refresh(course)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A course with this name already exists.",
        )

    return course


@router.delete(
    "/{course_id}",
    response_model=CourseResponse,
)
@limiter.limit("5/minute")
async def deactivate_course(
    request: Request,
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Course).where(Course.id == course_id)
    )

    course = result.scalar_one_or_none()

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )

    course.is_active = False

    await db.commit()
    await db.refresh(course)

    return course
