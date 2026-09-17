# Technical Reasoning & Architecture Decisions

## 1. The Core Problem & Solution
Cafés struggle with physical paper punch cards—they are easily lost, susceptible to fraud, and provide zero customer data. We solved this by building a **spend-based digital currency model**. 
* **The Math:** Customers earn 1 point for every ₹5 spent (a 20% return rate). 1 point = ₹1 in redemption value. This directly incentivizes higher ticket sizes rather than just frequent, low-value visits.

## 2. Tech Stack Rationale
* **Backend Framework (FastAPI / Python):** Chosen for its exceptional speed, built-in async support, and automatic OpenAPI documentation. Python allows for rapid iteration and clean business logic.
* **Database (SQLite -> SQLAlchemy):** We chose a Relational SQL database because loyalty points represent financial value. SQL guarantees strict ACID compliance. We avoid race conditions by logging every single earn/redeem event in an **immutable transaction ledger**, rather than just updating a single "points balance" integer.
* **Frontend (Jinja2 + HTMX + Tailwind CSS):** We intentionally avoided a heavy SPA framework like React. By using HTMX, we get the dynamic, page-load-free interactivity of a modern web app while keeping all routing and state management securely on the backend. Tailwind ensures a fast, mobile-responsive UI for cashiers and customers on the go.

## 3. Security & Authentication
* **Passwordless OTP:** Customers don't want to remember another password for a café. We implemented Phone + OTP login to remove friction at the counter.
* **Stateless Sessions (JWT):** Authentication is handled via JSON Web Tokens stored securely in HTTP-only cookies, protecting against XSS attacks while keeping the server stateless and highly scalable.

## 4. Handling Hackathon Twists
* **The `/clock` Endpoint (Inactivity Expiration):** Rather than running a constant, resource-heavy background cron job, we built an idempotent `/clock` endpoint. This allows the system to check for 90-day inactivity efficiently and batch-process point expirations.
* **The Outbox Pattern:** Instead of blocking the main thread to send emails during a busy transaction, tier-upgrade notifications are logged to a `NotificationOutbox` table. This allows a separate worker to process emails asynchronously, keeping the cashier's line moving fast.