# ☕ Cafe Rewards System

A full-stack digital loyalty and rewards platform built for a local café,
replacing paper punch cards with a spend-based points system, passwordless
phone login, and a real-time admin ledger.

Built for the **Vibe2Ship / INDIA RUNS** hackathon.

---

## How it works

1. A customer scans a static QR code at their table, which opens the web app.
2. They register (name, phone, email) or log in with just their **phone
   number + a one-time OTP** — no passwords.
3. Their dashboard shows their points balance and a personal QR code.
4. At checkout, the cashier scans that QR code on the admin console, enters
   the bill amount, and the system calculates and awards points automatically.
5. Every point added or deducted is written to an immutable transaction
   ledger, so there's never a dispute over a balance.

## Reward math

| Tier | Earn rate | Unlocked at |
|---|---|---|
| Standard | 0.2 points per ₹1 spent (1 point per ₹5) | Default |
| Platinum | 0.3 points per ₹1 spent | ₹5,000 lifetime spend |

- **1 point = ₹1** in redemption value (e.g. a ₹120 coffee costs 120 points).
- The earn rate applied to a purchase is the customer's tier **before** that
  purchase — so the transaction that crosses the Platinum threshold still
  earns at the standard rate, and only future purchases earn at 0.3/₹.
- Points **expire after 90 days of inactivity**. A grading/cron endpoint
  (`POST /clock`) zeroes out stale balances and logs an `expire` transaction
  for each one.
- Tier upgrades write a message to a notification outbox (`GET /outbox`)
  instead of sending a real email, so the flow is fully testable without an
  SMTP provider.

## Tech stack

- **Backend:** FastAPI (Python 3.10+)
- **ORM:** SQLAlchemy 2.0
- **Database:** SQLite for local dev (swap `DATABASE_URL` for MySQL in prod)
- **Templates:** Jinja2, server-rendered
- **Interactivity:** HTMX (no SPA build step)
- **Styling:** Tailwind CSS via CDN
- **Auth:** Phone + OTP, JWT in an HTTP-only cookie
- **QR codes:** Python `qrcode` library, rendered as base64 PNGs

## Project structure

```text
cafe-rewards-system/
├── app/
│   ├── main.py              # FastAPI app, page routes, /clock & /outbox
│   ├── config.py            # Settings, loaded from .env
│   ├── database.py          # SQLAlchemy engine & session
│   ├── models.py            # User, Transaction, NotificationOutbox
│   ├── schemas.py           # Pydantic request/response models
│   ├── crud.py               # All DB operations (tiers, ledger, expiry)
│   ├── auth.py               # OTP generation/verification, JWT, cookies
│   ├── utils.py               # QR code generation
│   ├── templating.py
│   ├── routers/
│   │   ├── auth.py            # /auth/register, /auth/otp/*, /auth/logout
│   │   ├── customer.py        # /customer/me, /customer/qr, /customer/transactions
│   │   └── admin.py           # /admin/transactions (earn / redeem)
│   └── templates/
│       ├── base.html
│       ├── login.html
│       ├── register.html
│       ├── customer_dashboard.html
│       └── admin_dashboard.html
├── seed_admin.py             # Bootstraps a cashier/admin account
├── grader_test.py            # Automated end-to-end test suite (see below)
├── requirements.txt
└── .env                      # Secrets & config (not committed)
```

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
# Edit .env and set a real SECRET_KEY:
python -c "import secrets; print(secrets.token_hex(32))"

# 4. Create the seeded admin/cashier account
python seed_admin.py
# -> Admin ready -> id=1 phone=9999999999 role=admin

# 5. Run the app
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000** in a browser. It redirects to `/login`;
new customers should go to **http://127.0.0.1:8000/register** first.

OTPs are never sent over SMS/email in local dev — they're printed straight
to the terminal running `uvicorn` (see `app/auth.py`), e.g.:

```
INFO:cafe_rewards.auth:OTP for 9876543210: 482913 (expires in 5 min)
```

## Testing the grading endpoints

Two endpoints exist specifically for automated grading and don't require
authentication:

- `POST /clock` — runs the 90-day inactivity expiry job. Returns
  `{"status": "ok", "expired_users_count": <int>}`.
- `GET /outbox` — returns every notification ever queued (tier upgrades,
  etc.) as a JSON list.

`grader_test.py` is a standalone script that exercises the **full** system
over real HTTP — registration, an admin-side earn transaction large enough
to trigger a Platinum tier upgrade, the resulting `/outbox` notification,
and a `/clock` run against a backdated test user — and prints a pass/fail
line per check.

To run it, with the server already up in another terminal:

```bash
pip install requests
python seed_admin.py    # if you haven't already
python grader_test.py
```

It exits with status code `0` if every check passes and `1` otherwise, so
it's CI-friendly. It authenticates by minting JWTs directly with the app's
own `create_access_token` (there's no HTTP endpoint to retrieve an OTP,
since real graders would get one over SMS/email) — everything it verifies
still goes through the real HTTP API surface.

## Known limitations / not yet built

- No real SMS/email gateway is wired up — OTP delivery and reward
  notifications are simulated (terminal logging / outbox table).
- The cashier enters a customer's QR code ID manually rather than scanning
  it with a device camera.
