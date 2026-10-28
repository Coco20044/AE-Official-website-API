from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.email import send_email
from uuid import UUID
import hashlib
from app.core.config import settings
from app.core.limiter import limiter
from fastapi.responses import HTMLResponse
from app.core.password_reset import create_password_reset_token,verify_password_reset_token
from app.schema.user import PasswordResetRequest,PasswordResetConfirm
from app.core.verification import verify_email_verification_token,create_email_verification_token
from app.core.security import (
    hash_password,
    create_access_token,
    verify_password,
)
from app.database.session import get_db
from app.models.user import User
from app.schema.user import (
    UserCreate,
    UserResponse,
    UserLogin,
    TokenResponse,
    UserUpdate,
    PasswordChange
    
)
from app.dependencies.auth import get_current_user

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post("/register", response_model=UserResponse,status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request:Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    email = str(user_data.email).lower()
    result = await db.execute(
        select(User).where(User.email == email)
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    new_user = User(
        name=user_data.name,
        email=email,
        phone_number=user_data.phone_number,
        password_hash=hash_password(user_data.password),
    )
    db.add(new_user)

    try:
        await db.commit()
        await db.refresh(new_user)

    except Exception:
        await db.rollback()
        raise

    verification_token = create_email_verification_token(
        str(new_user.id)
    )

    verification_link = (
        "http://127.0.0.1:8000/api/v1/users/verify-email"
        f"?token={verification_token}"
    )

    await send_email(
        to_email=new_user.email,
        subject="Verify Your AE Official Website Account",
        html_content=f"""
            <h2>Welcome to AE Official Website!</h2>

            <p>Hello {new_user.name},</p>

            <p>
                Thank you for creating an account.
                Please verify your email address by clicking
                the button below.
            </p>

            <p>
                <a href="{verification_link}"
                   style="
                       display: inline-block;
                       padding: 12px 20px;
                       background-color: #2563eb;
                       color: white;
                       text-decoration: none;
                       border-radius: 5px;
                   ">
                    Verify My Email
                </a>
            </p>

            <p>
                This verification link expires in 30 minutes.
            </p>

            <p>
                If you did not create this account, you can
                ignore this email.
            </p>
        """,
    )
    return new_user

   
@router.post("/login/oauth2", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login_oauth2(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    email = form_data.username.lower()

    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(
        form_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    access_token = create_access_token(str(user.id))

    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_my_account(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.patch("/me", response_model=UserResponse)
@limiter.limit("10/minute")
async def update_my_account(
    request: Request,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    update_data = user_data.model_dump(
        exclude_unset=True
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update.",
        )

    for field, value in update_data.items():
        if value is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be null.",
            )

    if "email" in update_data:
        update_data["email"] = str(
            update_data["email"]
        ).lower()

        result = await db.execute(
            select(User).where(
                User.email == update_data["email"],
                User.id != current_user.id,
            )
        )

        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
    for field, value in update_data.items():
        setattr(current_user, field, value)

    try:
        await db.commit()
        await db.refresh(current_user)
    except Exception:
        await db.rollback()
        raise
    return current_user


@router.patch("/me/password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(
        password_data.current_password,
        current_user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if verify_password(
        password_data.new_password,
        current_user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )

    current_user.password_hash = hash_password(
        password_data.new_password
    )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {
        "message": "Password changed successfully."
    }


@router.get("/verify-email")
@limiter.limit("5/minute")
async def verify_email(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    user_id = verify_email_verification_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired email verification token.",
        )

    try:
        user_uuid = UUID(user_id)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID in verification token.",
        )

    result = await db.execute(
        select(User).where(User.id == user_uuid)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.is_email_verified:
        return {
            "message": "Your email has already been verified."
        }

    user.is_email_verified = True

    await db.commit()

    return {
        "message": "Email verified successfully."
    }


@router.post("/password-reset/request")
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request,
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    email = str(reset_data.email).strip().lower()

    result = await db.execute(
        select(User).where(User.email == email)
    )

    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return {
            "message": (
                "If an account exists for this email, "
                "you will receive password reset instructions."
            )
        }

    reset_token = create_password_reset_token(
        str(user.id),
        user.password_hash
    )

    reset_link = (
        f"{settings.BASE_URL.rstrip('/')}"
        "/api/v1/users/password-reset/confirm"
        f"?token={reset_token}"
    )
    await send_email(
        to_email=user.email,
        subject="Reset Your AE Official Website Password",
        html_content=f"""
            <h2>Password Reset Request</h2>

            <p>Hello {user.name},</p>

            <p>
                We received a request to reset the password
                for your AE Official Website account.
            </p>

            <p>
                Click the button below to continue.
            </p>

            <p>
                <a href="{reset_link}"
                   style="
                       display: inline-block;
                       padding: 12px 20px;
                       background-color: #2563eb;
                       color: white;
                       text-decoration: none;
                       border-radius: 5px;
                   ">
                    Reset My Password
                </a>
            </p>

            <p>
                This link expires in 30 minutes.
            </p>

            <p>
                If you did not request a password reset,
                you can ignore this email.
            </p>
        """,
    )

    return {
        "message": (
            "If an account exists for this email, "
            "you will receive password reset instructions."
        )
    }


@router.post("/password-reset/confirm")
@limiter.limit("5/minute")
async def confirm_password_reset(
    request: Request,
    token: str,
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    token_data = verify_password_reset_token(token)

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )

    user_id, token_fingerprint = token_data

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID in password reset token.",
        )

    result = await db.execute(
        select(User).where(User.id == user_uuid)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account is inactive.",
        )

    current_fingerprint = hashlib.sha256(
        user.password_hash.encode("utf-8")
    ).hexdigest()

    if current_fingerprint != token_fingerprint:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset token has already been used or is no longer valid.",
        )

    user.password_hash = hash_password(reset_data.new_password)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {
        "message": "Password reset successfully."
    }
@router.get(
    "/password-reset/confirm",
    response_class=HTMLResponse,
)
async def password_reset_page(token: str):
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">

            <title>Reset Password | AE Official Website</title>

            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f4f1eb;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                }}

                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    width: 90%;
                    max-width: 400px;
                    box-sizing: border-box;
                }}

                h2 {{
                    text-align: center;
                    color: #171717;
                }}

                p {{
                    color: #696762;
                    line-height: 1.5;
                }}

                input, button {{
                    width: 100%;
                    padding: 12px;
                    margin-top: 12px;
                    box-sizing: border-box;
                    border-radius: 6px;
                }}

                input {{
                    border: 1px solid #ccc;
                }}

                button {{
                    background: #e86f51;
                    color: white;
                    border: none;
                    cursor: pointer;
                    font-size: 16px;
                }}

                #message {{
                    margin-top: 15px;
                    text-align: center;
                }}
            </style>
        </head>

        <body>
            <div class="container">
                <h2>Reset Your Password</h2>

                <p>
                    Enter your new password below.
                    It must contain at least 8 characters.
                </p>

                <form id="reset-form">
                    <input
                        type="password"
                        id="new-password"
                        placeholder="Enter new password"
                        minlength="8"
                        maxlength="128"
                        autocomplete="new-password"
                        required
                    >

                    <button type="submit">
                        Reset Password
                    </button>
                </form>

                <p id="message" role="status"></p>
            </div>

            <script>
                const token = "{token}";

                const form = document.getElementById("reset-form");
                const message = document.getElementById("message");
                const passwordInput =
                    document.getElementById("new-password");

                form.addEventListener("submit", async (event) => {{
                    event.preventDefault();

                    const newPassword = passwordInput.value;

                    message.textContent = "Resetting password...";

                    try {{
                        const response = await fetch(
                            "/api/v1/users/password-reset/confirm"
                            + "?token=" + encodeURIComponent(token),
                            {{
                                method: "POST",
                                headers: {{
                                    "Content-Type": "application/json"
                                }},
                                body: JSON.stringify({{
                                    new_password: newPassword
                                }})}}
                        );

                        const data = await response.json();

                        if (response.ok) {{
                            message.textContent =
                                "Your password has been reset successfully.";

                            form.reset();
                            form.style.display = "none";
                        }} else {{
                            message.textContent =
                                data.detail || "Unable to reset your password.";
                        }}
                    }} catch (error) {{
                        message.textContent =
                            "Unable to connect. Please try again.";
                    }}
                }});
            </script>
        </body>
        </html>
        """
    )
