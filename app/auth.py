"""
Passwordless auth: OTP generation/verification + JWT issuance via HTTP-only cookie.
"""
import logging
import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status, Request, Response
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, UserRole
from app import crud

logger = logging.getLogger("cafe_rewards.auth")
logging.basicConfig(level=logging.INFO)

otp_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------- OTP ----------

def _generate_otp_code() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(settings.OTP_LENGTH))


def request_otp(db: Session, phone_number: str) -> None:
    user = crud.get_user_by_phone(db, phone_number)
    if user is None:
        raise LookupError("No account found for this phone number. Register first.")

    otp_code = _generate_otp_code()
    otp_hash = otp_context.hash(otp_code)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    crud.set_user_otp(db, user, otp_hash=otp_hash, expires_at=expires_at)

    if settings.SIMULATE_EMAIL or settings.ENVIRONMENT == "development":
        logger.info("OTP for %s: %s (expires in %s min)",
                     phone_number, otp_code, settings.OTP_EXPIRE_MINUTES)
    else:
        pass  # TODO: real SMS gateway (Twilio/Msg91)


def verify_otp(db: Session, phone_number: str, otp_code: str) -> User:
    user = crud.get_user_by_phone(db, phone_number)
    if user is None or user.otp_code is None or user.otp_expires_at is None:
        raise ValueError("Invalid or expired OTP.")

    now = datetime.now(timezone.utc)
    expires_at = user.otp_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now > expires_at:
        crud.clear_user_otp(db, user)
        raise ValueError("OTP has expired. Request a new one.")

    if not otp_context.verify(otp_code, user.otp_code):
        raise ValueError("Invalid or expired OTP.")

    crud.clear_user_otp(db, user)
    return user


# ---------- JWT ----------

def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT != "development",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.COOKIE_NAME)


# ---------- Dependencies (API — raise on failure) ----------

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(settings.COOKIE_NAME)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    user = crud.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# ---------- Dependency (pages — returns None instead of raising) ----------

def get_current_user_for_page(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Same checks as get_current_user, but returns None on any failure so
    page routes can redirect to /login instead of showing a raw 401 JSON."""
    token = request.cookies.get(settings.COOKIE_NAME)
    if token is None:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None
    user = crud.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        return None
    return user