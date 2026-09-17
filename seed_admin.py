"""
Standalone hackathon bootstrap script — creates (or promotes) a single
admin/cashier account so you can test /admin/transactions without building
a role-assignment UI. Run once: python seed_admin.py
"""
from app.database import SessionLocal, Base, engine
from app.models import User, UserRole
from app import crud

ADMIN_PHONE = "9999999999"
ADMIN_EMAIL = "admin@localcafebrew.com"
ADMIN_NAME = "Cashier (Seeded Admin)"


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = crud.get_user_by_phone(db, ADMIN_PHONE)
        if user is None:
            user = User(phone_number=ADMIN_PHONE, email=ADMIN_EMAIL, full_name=ADMIN_NAME)
            db.add(user)

        user.role = UserRole.admin
        user.is_active = True
        db.commit()
        db.refresh(user)
        print(f"Admin ready -> id={user.id} phone={user.phone_number} role={user.role.value}")
    finally:
        db.close()


if __name__ == "__main__":
    main()