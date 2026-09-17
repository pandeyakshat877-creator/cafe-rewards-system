from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app import models  # noqa: F401
from app import crud
from app.templating import templates
from app.routers import auth as auth_router
from app.routers import customer as customer_router
from app.routers import admin as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Cafe Rewards", lifespan=lifespan)

app.include_router(auth_router.router)
app.include_router(customer_router.router)
app.include_router(admin_router.router)


@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@app.get("/health")
def health_check():
    return {"status": "ok"}


# ---------- Hackathon grading endpoints ----------

@app.post("/clock")
def run_clock(db: Session = Depends(get_db)):
    expired_count = crud.expire_stale_points(db)
    return {"status": "ok", "expired_users_count": expired_count}


@app.get("/outbox")
def get_outbox(db: Session = Depends(get_db)):
    notifications = crud.get_all_notifications(db)
    return {
        "notifications": [
            {
                "id": n.id,
                "user_id": n.user_id,
                "message": n.message,
                "is_sent": n.is_sent,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ]
    }