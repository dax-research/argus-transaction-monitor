# Argus Transaction Monitor

**Argus** is a full-stack fraud detection system that monitors payment transactions in real time. It uses a layered approach — a rule engine for hard violations and a trained ML ensemble model (Random Forest + XGBoost + Meta Logistic Regression) for nuanced risk scoring. Suspicious transactions trigger OTP challenges, and analysts review everything through a dedicated dashboard.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Running the Apps](#running-the-apps)
- [API Reference](#api-reference)
- [Fraud Detection Logic](#fraud-detection-logic)
- [ML Model](#ml-model)
- [Database Models](#database-models)
- [License](#license)

---

## Features

- **Real-time fraud detection** on every transaction
- **Two-tier rule engine** — hard-block rules for high-confidence fraud, soft risk-boost rules for contextual signals
- **ML ensemble model** — Random Forest + XGBoost stacked with a Meta Logistic Regression
- **OTP challenge** for medium-risk transactions (30%–70% risk score)
- **Customer App** — login, send money, view transaction history and balance
- **Analyst & Auditor Dashboards** — KPI cards, charts, transaction table, investigation case management, audit log
- **Staff roles** — Analysts (full investigation powers) vs Auditors (read-only, can escalate suspicious transactions)
- **OAuth2 + JWT authentication** for the staff dashboards (email/password + Google Sign-In; auditors can self-register, analysts are admin-provisioned)
- **Token authentication** for the customer app API

---

## Architecture

```
Customer App (port 3000)
       │
       ▼
Django REST API (port 8001)  ◄──── Analyst Dashboard (/dashboard/analyst/)
       │
       ├─ Rule Engine (Tier 1: hard-block | Tier 2: risk-boost)
       │
       ├─ ML Fraud Engine (RF + XGBoost + Meta-LR)
       │         combines ML risk + rule boost → final decision
       │
       ├─ OTP Service (challenge for 0.30–0.70 risk)
       │
       └─ Transaction Model (SQLite / MySQL)
```

**Decision thresholds:**

| Combined risk score | Decision |
|---|---|
| < 0.30 | ✅ ALLOW |
| 0.30 – 0.70 | ⚠️ CHALLENGE (OTP required) |
| > 0.70 | 🚫 DENY (BLOCKED) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.x, Django 6.x, Django REST Framework |
| ML | scikit-learn, XGBoost, joblib, pandas, numpy |
| Auth (staff dashboards) | django-oauth-toolkit issuing signed JWT access tokens |
| Auth (customer) | DRF Token authentication |
| Database | SQLite (dev) / MySQL (prod) |
| Frontend — Customer | Plain HTML + CSS + JS |
| Frontend — Analyst | Plain HTML + CSS + JS (Chart.js) |

---

## Project Structure

```
argus-transaction-monitor/
├── argus_transaction_monitor/   # Django project settings & URLs
│   ├── settings.py
│   ├── urls.py
│   └── cors_middleware.py
│
├── transactions/                # Core transaction processing
│   ├── models.py                # Transaction model
│   ├── views.py                 # process_transaction API
│   ├── urls.py
│   └── fraud/
│       ├── rules.py             # Two-tier rule engine
│       ├── evaluator.py         # Runs rules, returns hard_block + risk_boost
│       └── constant.py          # Thresholds (HIGH_AMOUNT, DAILY_LIMIT, etc.)
│
├── fraud_engine/                # ML fraud detection
│   └── services/
│       └── ml_rf_v1.py          # RF + XGBoost + Meta-LR ensemble
│
├── otp_service/                 # OTP generation and verification
├── analyst_dashboard/           # Analyst API (legacy endpoints)
├── frontend_api/                # JWT auth + dashboard API endpoints
│   ├── views.py                 # login, register, stats, transactions, etc.
│   └── urls.py
│
├── users/                       # Customer user model
├── ml_assests/                  # Trained model files (.joblib)
│
├── customer-app/                # Customer-facing static web app
│   ├── index.html               # Login page
│   ├── dashboard.html           # Send money + balance
│   └── history.html             # Transaction history
│
└── frontend/                    # Analyst dashboard static web app
    ├── templetes/
    │   ├── login.html
    │   ├── dashboard_analyst.html
    │   └── dashboard_auditor.html
    └── static/
        ├── css/style.css
        └── js/
            ├── auth.js
            ├── api.js
            └── dashboard_analyst.js
```

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd argus-transaction-monitor
```

### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / Mac
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply migrations

```bash
python manage.py migrate
```

### 5. Create an analyst superuser

```bash
python manage.py createsuperuser
```

Or use the existing default:
```
Email:    analyst@argus.com
Password: Analyst@123
```

> To create one manually via shell:
> ```bash
> python manage.py shell -c "
> from django.contrib.auth.models import User
> User.objects.create_superuser('analyst', 'analyst@argus.com', 'Analyst@123', first_name='Fraud', last_name='Analyst')
> "
> ```

### 6. (Optional) Retrain ML models

```bash
python retrain_models.py
```

---

## Running the Apps

### Backend (Django API)

```bash
python manage.py runserver 8001
```

### Customer App

```bash
cd customer-app
python -m http.server 3000
```

Open: **http://localhost:3000**

### Analyst Dashboard

No extra server needed — served by Django.

Open: **http://localhost:8001/login/**

---

## Staff Roles & Workflow

- **Analyst** — full access to dashboards, can update investigations, change case status, and manually flag transactions.
- **Auditor** — read-only access to dashboards and audit logs. Auditors can:
  - **Self-register** via `/api/auth/register/` (email/password or Google Sign-In) — they always become `AUDITOR` users.
  - **Report suspicious transactions** from the Auditor Transactions tab using the 🚩 Report button. This calls the flag API with a note describing why the transaction looks fraudulent.
- **Analyst notification flow**:
  - Each auditor report creates or updates an `Investigation` row tagged with `AUDITOR_FLAGGED: <note>`.
  - On the Analyst dashboard → **Investigation Cases**, analysts see a **Notifications** column; cases with auditor reports show an **“Auditor report”** badge and the details appear in the Notes field/modal.

---

## API Reference

### Customer App Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/users/login/` | Customer login |
| GET | `/api/profile/` | Get user profile & balance |
| POST | `/api/transaction/process/` | Submit a transaction |
| POST | `/api/verify-otp/` | Verify OTP for challenged transaction |
| GET | `/api/transactions/history/` | Transaction history |

### Analyst Dashboard Endpoints (JWT required)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login/` | Staff login (analyst / auditor) → OAuth2 JWT tokens |
| POST | `/api/auth/register/` | Self-service **auditor** signup; admins can also provision analysts |
| POST | `/api/auth/google/` | Google Sign-In / signup → creates or logs in **auditor** accounts |
| POST | `/api/auth/refresh/` | Refresh access token |
| POST | `/api/auth/logout/` | Blacklist refresh token |
| GET | `/api/dashboard/stats/` | KPI metrics + chart data |
| GET | `/api/dashboard/transactions/` | All transactions (filterable) |
| GET | `/api/dashboard/investigations/` | Blocked transactions as cases |
| PATCH | `/api/dashboard/investigations/<id>/` | Update case status |
| GET | `/api/dashboard/audit-log/` | Recent transaction audit trail |
| POST | `/api/dashboard/transactions/<txn_id>/flag/` | Manually flag a transaction for investigation; body may include `{ "note": "auditor/analyst comment" }` and is recorded on the Investigation |

---

## Fraud Detection Logic

### Tier 1 — Hard Block Rules (always DENY)

| Rule | Trigger |
|---|---|
| `high_amount_rule` | Amount ≥ ₹1,00,000 |
| `rapid_transactions_rule` | 5+ settled transactions in 5 minutes |
| `failed_attempts_rule` | 5+ FAILED transactions in 30 minutes |
| `daily_velocity_rule` | Daily SUCCESS total > ₹50,000 |

### Tier 2 — Soft Risk-Boost Rules (add to ML score)

| Rule | Risk added |
|---|---|
| `location_anomaly_boost` | City changed from last real transaction → +0.35 |
| `device_change_boost` | Unknown device type (2+ prior txns) → +0.30 |
| `payment_type_risk_boost` | UPI/Wallet > ₹5,000 → +0.20 |

**Final risk = min(1.0, ML score + total boost)**

---

## ML Model

The model lives in `fraud_engine/services/ml_rf_v1.py` and uses pre-trained joblib files in `ml_assests/`:

| File | Description |
|---|---|
| `argus_rf_model.joblib` | Random Forest base model |
| `argus_xgb_model.joblib` | XGBoost base model |
| `argus_meta_lr_model.joblib` | Meta Logistic Regression (stacked) |
| `argus_encoder.joblib` | Device type label encoder |

**Features used:** amount, daily transaction count, 7-day transaction count, 7-day average amount, is new device, is weekend, device type (encoded), hour of day.

To retrain: `python retrain_models.py` (requires `Fraud_dataset.csv` in project root)

---

## Database Models

### User (customer)
| Field | Type | Notes |
|---|---|---|
| `user_id` | CharField | Unique customer ID |
| `phone` | CharField | Phone number |
| `is_blocked` | BooleanField | Account blocked flag |
| `account_balance` | FloatField | Current balance |
| `created_at` | DateTimeField | Auto-generated |

### Transaction
| Field | Type | Notes |
|---|---|---|
| `txn_id` | CharField | Unique (e.g. TXN-XXXX) |
| `user` | ForeignKey | Links to User |
| `amount` | DecimalField | Transaction amount |
| `status` | CharField | INITIATED / SUCCESS / FAILED / OTP_REQUIRED / BLOCKED |
| `fraud_decision` | CharField | ALLOW / CHALLENGE / DENY |
| `risk_score` | FloatField | 0.0 – 1.0 |
| `device_type` | CharField | mobile / desktop / tablet |
| `city` | CharField | Transaction city |
| `payment_type` | CharField | UPI / WALLET / CARD / BANK |
| `otp_required` | BooleanField | OTP challenge triggered |
| `failure_reason` | CharField | Why it was blocked |
| `created_at` | DateTimeField | Auto-generated |

## Planned Security Enhancements

To ensure the platform is production-ready, the following security measures will be implemented in the future:

1. **Production Django Settings**: Setting `DEBUG = False`, enforcing secure cookies (`SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`), and enabling Strict Transport Security (HSTS).
2. **API Rate Limiting**: Adding DRF throttling to critical endpoints (like login and OTP verification) to prevent brute-force attacks.
3. **Database Migration**: Switching from SQLite to a robust relational database like PostgreSQL or MySQL for better concurrency and scale.
4. **Role-Based Access Control (RBAC) & Audit Logging**: Enforcing strict boundaries between Analyst and Auditor actions and maintaining an immutable `AuditLog` for staff activities.
5. **Multi-Factor Authentication (MFA) for Staff**: Requiring Analysts and Auditors to use authenticator apps or email OTPs when signing into the dashboard.
6. **Content Security Policy (CSP)**: Adding CSP headers to prevent Cross-Site Scripting (XSS) attacks on the frontend.

---

## License

MIT — see [LICENCE](LICENCE)
