from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UserRole
from app.schemas import UserRegister, OTPRequest, OTPVerify, UserOut
from app import crud, auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    try:
        return crud.create_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/otp/request")
def request_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    try:
        auth_service.request_otp(db, payload.phone_number)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"status": "otp_sent"}


@router.post("/otp/verify")
def verify_otp(payload: OTPVerify, response: Response, db: Session = Depends(get_db)):
    try:
        user = auth_service.verify_otp(db, payload.phone_number, payload.otp_code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    token = auth_service.create_access_token(user.id)
    auth_service.set_auth_cookie(response, token)

    redirect_to = "/admin/dashboard" if user.role == UserRole.admin else "/customer/dashboard"
    return {"status": "logged_in", "user_id": user.id, "redirect": redirect_to}


@router.post("/logout")
def logout(response: Response):
    auth_service.clear_auth_cookie(response)
    return {"status": "logged_out"}