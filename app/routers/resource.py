from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db

from app.dependencies.auth import get_current_user, get_current_admin

from app.models.cohort import Cohort

from app.models.enrollment import Enrollment

from app.models.learning_resource import LearningResource

from app.models.user import User,UserRole

from app.schema.learning_resource import(
    ResourceCreate, ResourceResponse, ResourceUpdate
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
            detail="You must be enrolled in this cohort to access its resources.",
        )


@router.post(
    "/",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_resource(
    resource_data: ResourceCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    cohort_result = await db.execute(
        select(Cohort).where(Cohort.id == resource_data.cohort_id)
    )
    cohort = cohort_result.scalar_one_or_none()

    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort not found.",
        )

    resource = LearningResource(
        cohort_id=resource_data.cohort_id,
        title=resource_data.title,
        description=resource_data.description,
        resource_url=str(resource_data.resource_url),
        resource_type=resource_data.resource_type,
    )

    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    return resource


@router.get(
    "/cohort/{cohort_id}",
    response_model=list[ResourceResponse],
)
async def get_cohort_resources(
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
    if current_user.role!=UserRole.ADMIN: 
        await check_student_enrollment(
            db,
            current_user.id,
            cohort_id,
        )

    result = await db.execute(
        select(LearningResource)
        .where(
            LearningResource.cohort_id == cohort_id,
            LearningResource.is_active.is_(True),
        )
        .order_by(LearningResource.created_at.desc())
    )

    return result.scalars().all()


@router.get(
    "/{resource_id}",
    response_model=ResourceResponse,
)
async def get_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(LearningResource).where(
            LearningResource.id == resource_id,
            LearningResource.is_active.is_(True),
        )
    )

    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning resource not found.",
        )
    if current_user.role!=UserRole.ADMIN: 
        await check_student_enrollment(
            db,
            current_user.id,
            resource.cohort_id,
        )

    return resource

@router.patch(
    "/{resource_id}",
    response_model=ResourceResponse,
)
async def update_resource(
    resource_id: UUID,
    resource_data: ResourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(LearningResource).where(
            LearningResource.id == resource_id
        )
    )

    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning resource not found.",
        )

    update_data = resource_data.model_dump(exclude_unset=True)

    if (
        "resource_url" in update_data
        and update_data["resource_url"] is not None
    ):
        update_data["resource_url"] = str(
            update_data["resource_url"]
        )

    for field, value in update_data.items():
        setattr(resource, field, value)

    await db.commit()
    await db.refresh(resource)

    return resource


@router.delete(
    "/{resource_id}",
    status_code=status.HTTP_200_OK,
)
async def deactivate_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(LearningResource).where(
            LearningResource.id == resource_id
        )
    )

    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning resource not found.",
        )

    resource.is_active = False

    await db.commit()

    return {
        "message": "Learning resource deactivated successfully."
    }
