from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status,Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.limiter import limiter
from app.database.session import get_db
from app.dependencies.auth import get_current_admin
from app.models.cohort import Cohort
from app.models.course import Course
from app.models.user import User
from app.schema.cohort import CohortCreate, CohortUpdate, CohortResponse

router = APIRouter()


@router.post(
    "/",
    response_model=CohortResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def create_cohort(
    request: Request,
    cohort_data: CohortCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    course_result = await db.execute(
        select(Course).where(
            Course.id == cohort_data.course_id,
            Course.is_active.is_(True),
        )
    )
    course = course_result.scalar_one_or_none()
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active course not found.",
        )

    cohort = Cohort(
        name=cohort_data.name,
        course_id=cohort_data.course_id,
        start_date=cohort_data.start_date,
        end_date=cohort_data.end_date,
    )

    db.add(cohort)

    try:
        await db.commit()
        await db.refresh(cohort)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create cohort. Check the supplied information.",
        )

    return cohort


@router.get("/", response_model=list[CohortResponse])
@limiter.limit("30/minute")
async def get_cohorts(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Cohort)
        .where(Cohort.is_active.is_(True))
        .order_by(Cohort.start_date)
    )
    return result.scalars().all()


@router.get("/{cohort_id}", response_model=CohortResponse)
@limiter.limit("30/minute")
async def get_cohort(
    request: Request,
    cohort_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Cohort).where(
            Cohort.id == cohort_id,
            Cohort.is_active.is_(True),
        )
    )
    cohort = result.scalar_one_or_none()

    if cohort is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort not found.",
        )

    return cohort


@router.patch("/{cohort_id}", response_model=CohortResponse)
@limiter.limit("10/minute")
async def update_cohort(
    request: Request,
    cohort_id: UUID,
    cohort_data: CohortUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Cohort).where(Cohort.id == cohort_id)
    )
    cohort = result.scalar_one_or_none()

    if cohort is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort not found.",
        )

    updates = cohort_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields supplied.",
        )

    if any(value is None for value in updates.values()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cohort fields cannot be set to null.",
        )

    if "course_id" in updates:
        course_result = await db.execute(
            select(Course).where(
                Course.id == updates["course_id"],
                Course.is_active.is_(True),
            )
        )

        course = course_result.scalar_one_or_none()

        if course is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active course not found.",
            )

    new_start = updates.get("start_date", cohort.start_date)
    new_end = updates.get("end_date", cohort.end_date)

    if new_end < new_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="End date cannot be before start date.",
        )

    for field, value in updates.items():
        setattr(cohort, field, value)

    try:
        await db.commit()
        await db.refresh(cohort)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update cohort. Check the supplied information.",
        )

    return cohort


@router.delete("/{cohort_id}", response_model=CohortResponse)
@limiter.limit("5/minute")
async def deactivate_cohort(
    request: Request,
    cohort_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Cohort).where(Cohort.id == cohort_id)
    )
    cohort = result.scalar_one_or_none()

    if cohort is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort not found.",
        )

    cohort.is_active = False

    await db.commit()
    await db.refresh(cohort)

    return cohort
