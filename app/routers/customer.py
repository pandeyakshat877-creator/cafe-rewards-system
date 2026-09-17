from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserOut, TransactionOut
from app import crud, utils
from app.auth import get_current_user, get_current_user_for_page
from app.templating import templates

router = APIRouter(prefix="/customer", tags=["customer"])

# ---------- JSON API ----------

@router.get("/me", response_model=UserOut)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/qr")
def get_my_qr_code(current_user: User = Depends(get_current_user)):
    return {
        "qr_code_id": current_user.qr_code_id,
        "qr_image_base64": utils.generate_qr_code_base64(current_user.qr_code_id),
    }

@router.get("/transactions", response_model=list[TransactionOut])
def get_my_transactions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return crud.get_transactions_for_user(db, current_user.id)

# ---------- HTML pages ----------

@router.get("/dashboard", response_class=HTMLResponse)
def customer_dashboard_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_for_page),
    db: Session = Depends(get_db),
):
    if current_user is None:
        return RedirectResponse(url="/login")

    transactions = crud.get_transactions_for_user(db, current_user.id)
    qr_base64 = utils.generate_qr_code_base64(current_user.qr_code_id)

    # Fixed TemplateResponse with 'request' as the first argument
    return templates.TemplateResponse(
        request,
        "customer_dashboard.html",
        {
            "user": current_user,
            "qr_image_base64": qr_base64,
            "transactions": transactions,
            "next_tier_target": crud.PLATINUM_THRESHOLD,
        },
    )

@router.get("/points-fragment", response_class=HTMLResponse)
def points_fragment(current_user: User | None = Depends(get_current_user_for_page)):
    if current_user is None:
        return HTMLResponse('<span class="text-red-600 text-sm">Session expired</span>', status_code=401)
    return HTMLResponse(f'<span id="points-balance">{current_user.points_balance}</span>')