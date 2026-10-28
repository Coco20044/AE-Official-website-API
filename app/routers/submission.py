from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.dependencies.auth import get_current_user, get_current_admin
from app.models.assignment import Assignment
from app.models.enrollment import Enrollment
from app.models.submission import Submission
from app.models.user import User
from app.schema.submission import (
    SubmissionCreate,
    SubmissionUpdate,
    SubmissionResponse,
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
            detail="You must be enrolled in this cohort to submit assignments.",
        )


@router.post(
    "/",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_submission(
    submission_data: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Find the assignment
    assignment_result = await db.execute(
        select(Assignment).where(
            Assignment.id == submission_data.assignment_id,
            Assignment.is_active.is_(True),
        )
    )
    assignment = assignment_result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found.",
        )

    await check_student_enrollment(
        db,
        current_user.id,
        assignment.cohort_id,
    )
    if assignment.deadline is not None:
        from datetime import datetime, timezone

        if assignment.deadline <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The submission deadline has passed.",
            )


    existing_result = await db.execute(
        select(Submission).where(
            Submission.assignment_id == assignment.id,
            Submission.student_id == current_user.id,
        )
    )

    existing_submission = existing_result.scalar_one_or_none()

    if existing_submission:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted this assignment. Update your existing submission instead.",
        )
    submission = Submission(
        assignment_id=assignment.id,
        student_id=current_user.id,
        content=submission_data.content,
        submission_url=(
            str(submission_data.submission_url)
            if submission_data.submission_url
            else None
        ),
    )

    db.add(submission)
    await db.commit()
    await db.refresh(submission)


@router.get(
    "/my/{assignment_id}",
    response_model=SubmissionResponse,
)
async def get_my_submission(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    await check_student_enrollment(
        db,
        current_user.id,
        assignment.cohort_id,
    )

    submission_result = await db.execute(
        select(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.student_id == current_user.id,
        )
    )

    submission = submission_result.scalar_one_or_none()

    if not submission:
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not submitted this assignment yet.",
        )

    return submission
    

@router.get(
    "/assignment/{assignment_id}",
    response_model=list[SubmissionResponse],
)
async def get_assignment_submissions(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
   assignment_result = await db.execute(
      select(Assignment).where(
          Assignment.id == assignment_id
      )
  )
   assignment = assignment_result.scalar_one_or_none()

   if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found.",
        )

   result = await db.execute(
        select(Submission)
        .where(Submission.assignment_id == assignment_id)
        .order_by(Submission.submitted_at.desc())
    )

   return result.scalars().all()
@router.patch(
"/{submission_id}",
response_model=SubmissionResponse,
)
async def update_submission(
submission_id: UUID,
submission_data: SubmissionUpdate,
db: AsyncSession = Depends(get_db),
current_user: User = Depends(get_current_user),
):
    result = await db.execute(
    select(Submission).where(
    Submission.id == submission_id
    )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found.",
        )

    if submission.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own submission.",
        )

    assignment_result = await db.execute(
        select(Assignment).where(
            Assignment.id == submission.assignment_id
        )

    )
    assignment = assignment_result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found.",
        )


    if assignment.deadline is not None:
        from datetime import datetime, timezone

        if assignment.deadline <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The submission deadline has passed. Your submission can no longer be updated.",
            )

    update_data = submission_data.model_dump(
        exclude_unset=True
    )

    if (
        "submission_url" in update_data
        and update_data["submission_url"] is not None
    ):
        update_data["submission_url"] = str(
            update_data["submission_url"]
        )

    for field, value in update_data.items():
        setattr(submission, field, value)

    await db.commit()
    await db.refresh(submission)

    return submission
