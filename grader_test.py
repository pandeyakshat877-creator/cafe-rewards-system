"""
Standalone end-to-end grader simulation for the Cafe Rewards hackathon build.

WHY THIS ISN'T *PURE* HTTP
---------------------------
A real hackathon grader only gets HTTP access and would need an OTP
delivered by SMS/email to log in. Locally, OTPs only ever hit the
terminal via `logging` (see app/auth.py) — there's no endpoint to fetch
one. Likewise, there's no HTTP endpoint to fast-forward 90 days so
/clock has something to expire. This script closes those two gaps
exactly the way a real CI suite would:

  1. It imports `app.auth.create_access_token` directly to mint a
     session JWT — same secret, same payload shape as a real OTP login
     produces. Zero behavioural difference from the real thing.
  2. It uses SQLAlchemy (the app's own session/models) to backdate one
     test user's `last_activity_date`, since there is no "time travel"
     endpoint.

Every endpoint actually being graded — /health, /auth/register,
/admin/transactions, /clock, /outbox — is exercised purely over HTTP
with `requests`, exactly as the real grader will call it.

SETUP
-----
1. In one terminal:   uvicorn app.main:app --reload
2. Make sure the seeded admin exists:  python seed_admin.py
3. In another terminal, from the project root:  python grader_test.py

Exits 0 if every check passes, 1 otherwise (CI-friendly).
"""
import random
import string
import sys
from datetime import datetime, timedelta

import requests

from app.auth import create_access_token
from app.config import settings
from app.database import SessionLocal
from app.models import User, UserRole
from app import crud

BASE_URL = "http://127.0.0.1:8000"
ADMIN_PHONE = "9999999999"  # matches seed_admin.py

results: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    results.append(status)
    suffix = f" — {detail}" if detail and status == "FAIL" else ""
    print(f"[{status}] {label}{suffix}")
    return condition


def random_phone() -> str:
    return "9" + "".join(random.choices(string.digits, k=9))


def random_email() -> str:
    return f"grader_{random.randint(10_000, 99_999)}@example.com"


def authenticated_session(user_id: int) -> requests.Session:
    """Mints a real JWT the same way app/auth.py does and drops it in
    as the same cookie the browser would carry after a real OTP login."""
    session = requests.Session()
    token = create_access_token(user_id)
    session.cookies.set(settings.COOKIE_NAME, token)
    return session


def main() -> None:
    # ---------- 0. Is the server even up? ----------
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
    except requests.exceptions.ConnectionError:
        print("Could not reach the server. Start it first:\n  uvicorn app.main:app --reload")
        sys.exit(1)
    check("GET /health returns status ok", r.status_code == 200 and r.json().get("status") == "ok", r.text)

    db = SessionLocal()

    # ---------- 1. Confirm the seeded admin exists ----------
    admin = crud.get_user_by_phone(db, ADMIN_PHONE)
    if admin is None or admin.role != UserRole.admin:
        print("No seeded admin found. Run `python seed_admin.py` first.")
        db.close()
        sys.exit(1)
    admin_session = authenticated_session(admin.id)

    # ---------- 2. Register a fresh customer over real HTTP ----------
    phone, email = random_phone(), random_email()
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "phone_number": phone, "email": email, "full_name": "Grader Test Customer",
    })
    check("POST /auth/register creates a customer (201)", r.status_code == 201, r.text)
    customer = r.json()

    customer_session = authenticated_session(customer["id"])
    r = customer_session.get(f"{BASE_URL}/customer/me")
    check(
        "Authenticated GET /customer/me returns our test user",
        r.status_code == 200 and r.json().get("phone_number") == phone,
        r.text,
    )

    # ---------- 3. Earn enough to cross the Platinum threshold (>=₹5000) ----------
    # Triggers a tier upgrade -> a NotificationOutbox row, per crud.create_earn_transaction.
    r = admin_session.post(f"{BASE_URL}/admin/transactions", json={
        "user_qr_code_id": customer["qr_code_id"], "type": "earn", "amount_spent": 5000,
    })
    check("Admin POST /admin/transactions (earn ₹5000) succeeds (201)", r.status_code == 201, r.text)
    txn = r.json()
    check(
        "Earn transaction awards 1000 pts at the standard 0.2 pts/₹ rate",
        txn.get("points_added") == 1000,
        str(txn),
    )

    # ---------- 4. GET /outbox and look for that tier-upgrade notification ----------
    r = requests.get(f"{BASE_URL}/outbox")
    check(
        "GET /outbox returns 200 with a notifications list",
        r.status_code == 200 and isinstance(r.json().get("notifications"), list),
        r.text,
    )
    notifications = r.json().get("notifications", [])
    match = [
        n for n in notifications
        if n.get("user_id") == customer["id"] and "Platinum" in n.get("message", "")
    ]
    check(
        "Outbox contains this customer's Platinum tier-upgrade notification",
        len(match) == 1,
        str(notifications[-3:]),
    )

    # ---------- 5. Backdate a second user, then verify /clock expires them ----------
    stale_phone, stale_email = random_phone(), random_email()
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "phone_number": stale_phone, "email": stale_email, "full_name": "Grader Stale Customer",
    })
    check("Register second test customer for the expiry scenario", r.status_code == 201, r.text)
    stale_customer = r.json()

    # The one piece of setup with no HTTP equivalent: give them a balance
    # and push their last activity past the 90-day cutoff.
    stale_user = db.get(User, stale_customer["id"])
    stale_user.points_balance = 250
    stale_user.last_activity_date = datetime.utcnow() - timedelta(days=91)
    db.commit()

    r = requests.post(f"{BASE_URL}/clock")
    check("POST /clock returns 200 with status ok", r.status_code == 200 and r.json().get("status") == "ok", r.text)
    body = r.json()
    check("/clock response has an integer expired_users_count", isinstance(body.get("expired_users_count"), int), str(body))
    check("/clock expired at least our seeded stale user", body.get("expired_users_count", 0) >= 1, str(body))

    db.refresh(stale_user)
    check("Stale user's points_balance was zeroed by /clock", stale_user.points_balance == 0, f"balance={stale_user.points_balance}")

    # Idempotency — matches the guarantee documented in crud.expire_stale_points.
    r2 = requests.post(f"{BASE_URL}/clock")
    check(
        "/clock is idempotent — calling it again expires 0 more users",
        r2.status_code == 200 and r2.json().get("expired_users_count") == 0,
        r2.text,
    )

    db.close()

    # ---------- Summary ----------
    total, passed = len(results), results.count("PASS")
    print(f"\n{passed}/{total} checks passed.")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()