from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user, get_current_admin
from app.models.assignment import Assignment
from app.models.cohort import Cohort
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schema.assignment import (
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentResponse,
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
            detail="You must be enrolled in this cohort to access its assignments.",
        )


@router.post(
    "/",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment(
    assignment_data: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    cohort_result = await db.execute(
        select(Cohort).where(
            Cohort.id == assignment_data.cohort_id
        )
    )

    cohort = cohort_result.scalar_one_or_none()

    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort not found.",
        )

    assignment = Assignment(
        cohort_id=assignment_data.cohort_id,
        title=assignment_data.title,
        description=assignment_data.description,
        instructions=assignment_data.instructions,
        attachment_url=(
            str(assignment_data.attachment_url)
            if assignment_data.attachment_url
            else None
        ),
        deadline=assignment_data.deadline,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    return assignment


@router.get(
    "/cohort/{cohort_id}",
    response_model=list[AssignmentResponse],
)
async def get_cohort_assignments(
    cohort_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cohort_result = await db.execute(
        select(Cohort).where(Cohort.id == cohort_id)
    )

    cohort = cohort_result.scalar_one_or_none()

    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort not found.",
        )
    if current_user.role!="admin":
        await check_student_enrollment(
            db,
            current_user.id,
            cohort_id,
        )

    result = await db.execute(
        select(Assignment)
        .where(
            Assignment.cohort_id == cohort_id,
            Assignment.is_active.is_(True),
        )
        .order_by(Assignment.created_at.desc())
    )

    return result.scalars().all()


@router.get(
    "/{assignment_id}",
    response_model=AssignmentResponse,
)
async def get_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Assignment).where(
            Assignment.id == assignment_id,
            Assignment.is_active.is_(True),
        )
    )

    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found.",
        )
    if current_user.role!="admin":
        await check_student_enrollment(
            db,
            current_user.id,
            assignment.cohort_id,
        )

    return assignment


@router.patch(
    "/{assignment_id}",
    response_model=AssignmentResponse,
)
async def update_assignment(
    assignment_id: UUID,
    assignment_data: AssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Assignment).where(
            Assignment.id == assignment_id
        )
    )

    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found.",
        )

    update_data = assignment_data.model_dump(
        exclude_unset=True
    )

    if (
        "attachment_url" in update_data
        and update_data["attachment_url"] is not None
    ):
        update_data["attachment_url"] = str(
            update_data["attachment_url"]
        )

    for field, value in update_data.items():
        setattr(assignment, field, value)

    await db.commit()
    await db.refresh(assignment)

    return assignment


# Deactivate an assignment
@router.delete(
    "/{assignment_id}",
    status_code=status.HTTP_200_OK,
)
async def deactivate_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Assignment).where(
            Assignment.id == assignment_id
        )
    )

    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found.",
        )

    assignment.is_active = False

    await db.commit()

    return {
        "message": "Assignment deactivated successfully."
    }
