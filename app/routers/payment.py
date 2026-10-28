import secrets
from decimal import Decimal
from uuid import UUID
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.core.config import settings
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User,UserRole
from app.models.enrollment import Enrollment
from app.models.cohort import Cohort
from app.models.course import Course
from app.models.payment import Payment
from app.schema.payment import PaymentInitializationResponse,PaymentInitializationRequest,PaymentVerificationResponse
from fastapi import Request
from app.core.limiter import limiter

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


@router.post(
    "/initialize",
    response_model=PaymentInitializationResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def initialize_payment(
    request: Request,
    payment_data: PaymentInitializationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can initiate course payments.",
        )
    enrollment_result = await db.execute(
        select(Enrollment).where(
            Enrollment.id == payment_data.enrollment_id,
            Enrollment.student_id == current_user.id,
        )
    )

    enrollment = enrollment_result.scalar_one_or_none()
    if enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found.",
        )
    if enrollment.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="only pending enrollments are eligible for .",
        )
    cohort_result = await db.execute(
        select(Cohort).where(
            Cohort.id == enrollment.cohort_id
        )
    )

    cohort = cohort_result.scalar_one_or_none()

    if cohort is None or not cohort.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This cohort is not available for payment.",
        )
    course_result = await db.execute(
        select(Course).where(
            Course.id == cohort.course_id
        )
    )

    course = course_result.scalar_one_or_none()

    if course is None or not course.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This course is not available for payment.",
        )
    course_price = Decimal(str(course.price))

    if course_price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This course does not have a valid price.",
        )
    amount_kobo = int(course_price * Decimal("100"))
    reference = secrets.token_urlsafe(24)
    payload = {
        "email": current_user.email,
        "amount": amount_kobo,
        "currency": "NGN",
        "reference": reference,
        "metadata": {
            "enrollment_id": str(enrollment.id),
            "course_id": str(course.id),
            "cohort_id": str(cohort.id),
        },
    }

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.paystack.co/transaction/initialize",
                json=payload,
                headers=headers,
            )

            response.raise_for_status()
            paystack_result = response.json()

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Paystack could not initialize the payment.",
        ) from exc

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to connect to Paystack. Please try again.",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Paystack returned an invalid response.",
        ) from exc

    if not isinstance(paystack_result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Paystack returned an invalid response.",
        )

    if paystack_result.get("status") is not True:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Paystack could not initialize the payment.",
        )

    data = paystack_result.get("data")

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Paystack returned incomplete payment details.",
        )

    authorization_url = data.get("authorization_url")
    access_code = data.get("access_code")
    paystack_reference = data.get("reference")

    if not all(
        isinstance(value, str) and value
        for value in (
            authorization_url,
            access_code,
            paystack_reference,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Paystack returned incomplete payment details.",
        )

    payment = Payment(
        student_id=current_user.id,
        enrollment_id=enrollment.id,
        amount=amount_kobo,
        currency="NGN",
        status="pending",
        reference=paystack_reference,
        paystack_access_code=access_code,
        authorization_url=authorization_url,
    )

    try:
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

    except Exception as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save the payment record.",
        ) from exc
    return PaymentInitializationResponse(
        reference=payment.reference,
        authorization_url=payment.authorization_url,
        access_code=payment.paystack_access_code,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
    )


@router.get(
    "/verify"
)
@limiter.limit("10/minute")
async def verify_payment(
    request:Request,
    reference: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can verify their payments.",
        )

    result = await db.execute(
        select(Payment).where(
            Payment.reference == reference,
            Payment.student_id == current_user.id,
        )
    )
    payment = result.scalar_one_or_none()

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    if payment.status == "success":
        return payment

    if not settings.PAYSTACK_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment service is not configured.",
        )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"https://api.paystack.co/transaction/verify/{payment.reference}",
                headers={
                    "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            paystack_result = response.json()

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Paystack could not verify the payment.",
        ) from exc

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to connect to Paystack.",
        ) from exc

    if not isinstance(paystack_result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Paystack returned an invalid response.",
        )

    if paystack_result.get("status") is not True:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Paystack could not verify the transaction.",
        )

    data = paystack_result.get("data")

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Paystack returned invalid transaction data.",
        )

    if data.get("reference") != payment.reference:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction reference does not match.",
        )

    if data.get("amount") != payment.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction amount does not match.",
        )

    if data.get("currency") != payment.currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction currency does not match.",
        )

    transaction_status = data.get("status")

    if transaction_status == "success":
        payment.status = "success"
        payment.paid_at = datetime.now(timezone.utc)

        enrollment_result = await db.execute(
            select(Enrollment).where(
                Enrollment.id == payment.enrollment_id,
                Enrollment.student_id == current_user.id,
            )
        )
        enrollment = enrollment_result.scalar_one_or_none()
        if enrollment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found.",
            )
        enrollment.status = "enrolled"
        await db.commit()
        await db.refresh(payment)

    elif transaction_status in {"failed", "abandoned"}:
        payment.status = "failed"

        await db.commit()
        await db.refresh(payment)

    return payment
