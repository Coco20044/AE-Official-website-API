from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.dependencies.auth import get_current_user, get_current_admin
from app.models.cohort import Cohort
from app.models.enrollment import Enrollment
from app.models.user import User, UserRole
from app.schema.enrollment import EnrollmentCreate, EnrollmentResponse,AdminEnrollmentCreate,EnrollmentUpdate
from fastapi import Request
from app.core.limiter import limiter

router = APIRouter()


@router.post(
    "/",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def enroll_in_cohort(
    request:Request,
    enrollment_data: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can enroll themselves.",
        )

    cohort_result = await db.execute(
        select(Cohort).where(
            Cohort.id == enrollment_data.cohort_id,
            Cohort.is_active == True,
        )
    )
    cohort = cohort_result.scalar_one_or_none()

    if cohort is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active cohort not found.",
        )

    existing_result = await db.execute(
        select(Enrollment).where(
            Enrollment.student_id == current_user.id,
            Enrollment.cohort_id == enrollment_data.cohort_id,
        )
    )
    existing_enrollment = existing_result.scalar_one_or_none()

    if existing_enrollment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already enrolled in this cohort.",
        )

    new_enrollment = Enrollment(
        student_id=current_user.id,
        cohort_id=enrollment_data.cohort_id,
        status="pending"
    )

    db.add(new_enrollment)

    try:
        await db.commit()
        await db.refresh(new_enrollment)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already enrolled in this cohort.",
        )

    return new_enrollment


@router.post(
    "/admin",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_enroll_student(
    enrollment_data: AdminEnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    student_result = await db.execute(
        select(User).where(
            User.id == enrollment_data.student_id,
            User.role == UserRole.STUDENT,
        )
    )
    student = student_result.scalar_one_or_none()

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found.",
        )

    cohort_result = await db.execute(
        select(Cohort).where(
            Cohort.id == enrollment_data.cohort_id,
            Cohort.is_active == True,
        )
    )
    cohort = cohort_result.scalar_one_or_none()

    if cohort is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active cohort not found.",
        )

    existing_result = await db.execute(
        select(Enrollment).where(
            Enrollment.student_id == enrollment_data.student_id,
            Enrollment.cohort_id == enrollment_data.cohort_id,
        )
    )
    existing_enrollment = existing_result.scalar_one_or_none()

    if existing_enrollment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already enrolled in this cohort.",
        )

    new_enrollment = Enrollment(
        student_id=enrollment_data.student_id,
        cohort_id=enrollment_data.cohort_id,
        status="enrolled"
    )

    db.add(new_enrollment)

    try:
        await db.commit()
        await db.refresh(new_enrollment)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already enrolled in this cohort.",
        )

    return new_enrollment


@router.get(
    "/me",
    response_model=list[EnrollmentResponse],
)
@limiter.limit("30/minute")
async def get_my_enrollments(
    request:Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == current_user.id)
        .order_by(Enrollment.enrolled_at.desc())
    )

    enrollments = result.scalars().all()

    return enrollments


@router.get(
    "/",
    response_model=list[EnrollmentResponse],
)
@limiter.limit("30/minute")
async def get_all_enrollments(
    request:Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Enrollment).order_by(
            Enrollment.enrolled_at.desc()
        )
    )

    enrollments = result.scalars().all()

    return enrollments


@router.get(
    "/{enrollment_id}",
    response_model=EnrollmentResponse,
)
@limiter.limit("30/minute")
async def get_enrollment(
    request:Request,
    enrollment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.id == enrollment_id
        )
    )

    enrollment = result.scalar_one_or_none()

    if enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found.",
        )

    return enrollment


@router.patch(
    "/{enrollment_id}",
    response_model=EnrollmentResponse,
)
@limiter.limit("10/minute")
async def update_enrollment(
    request:Request,
    enrollment_id: UUID,
    enrollment_data: EnrollmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.id == enrollment_id
        )
    )

    enrollment = result.scalar_one_or_none()

    if enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found.",
        )

    enrollment.status = enrollment_data.status

    await db.commit()
    await db.refresh(enrollment)

    return enrollment
