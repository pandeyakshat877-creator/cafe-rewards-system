from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole, TransactionType
from app.schemas import TransactionCreate, TransactionOut
from app import crud
from app.auth import require_admin, get_current_user_for_page
from app.templating import templates

router = APIRouter(prefix="/admin", tags=["admin"])

# ---------- JSON API ----------

@router.post("/transactions", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def post_transaction(
    payload: TransactionCreate,
    staff: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    customer = crud.get_user_by_qr_code(db, payload.user_qr_code_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No customer found for this QR code.")

    try:
        if payload.type == TransactionType.earn:
            return crud.create_earn_transaction(db, customer, staff, payload.amount_spent)
        return crud.create_redeem_transaction(db, customer, staff, payload.points_to_redeem)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

# ---------- HTML page ----------

@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_for_page),
):
    if current_user is None:
        return RedirectResponse(url="/login")
    if current_user.role != UserRole.admin:
        return RedirectResponse(url="/login")

    # Fixed TemplateResponse with 'request' as the first argument
    return templates.TemplateResponse(
        request, "admin_dashboard.html", {"staff": current_user}
    )