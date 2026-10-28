from datetime import datetime, timedelta, timezone
import hashlib
import jwt

from app.core.config import settings

ALGORITHM = "HS256"

PASSWORD_RESET_EXPIRE_MINUTES = 30


def create_password_reset_token(
    user_id: str,
    password_hash: str,
) -> str:
    now = datetime.now(timezone.utc)

    password_fingerprint = hashlib.sha256(
        password_hash.encode("utf-8")
    ).hexdigest()

    payload = {
        "sub": user_id,
        "type": "password_reset",
        "password_fingerprint": password_fingerprint,
        "iat": now,
        "exp": now + timedelta(
            minutes=PASSWORD_RESET_EXPIRE_MINUTES
        ),
    }


    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )

    
    return token


def verify_password_reset_token(
    token: str,
) -> tuple[str, str] | None:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        if payload.get("type") != "password_reset":
            return None

        user_id = payload.get("sub")

        password_fingerprint = payload.get(
            "password_fingerprint"
        )

        if not user_id or not password_fingerprint:
            return None

        return user_id, password_fingerprint

    except jwt.InvalidTokenError:
        return None
