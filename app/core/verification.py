from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

ALGORITHM = "HS256"
EMAIL_VERIFICATION_EXPIRE_MINUTES = 30


def create_email_verification_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "email_verification",
        "iat": now,
        "exp": now + timedelta(
            minutes=EMAIL_VERIFICATION_EXPIRE_MINUTES
        ),
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return token


def verify_email_verification_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        if payload.get("type") != "email_verification":
            return None

        user_id = payload.get("sub")

        if not user_id:
            return None

        return user_id

    except jwt.InvalidTokenError:
        return None
