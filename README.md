# Argus-Transaction-Monitor

**Argus** is a Django-based fraud detection system that monitors payment transactions, performs risk scoring using machine learning, triggers OTP challenges for suspicious transactions, and allows analyst review through a web admin interface.  

This project is designed as a modular system to integrate with dummy or real payment apps for learning, testing, and fraud monitoring purposes.

---

## Table of Contents

- [Features](#features)  
- [Tech Stack](#tech-stack)  
- [Architecture](#architecture)  
- [Setup](#setup)  
- [Database](#database)  
- [Models](#models)  
- [Admin Dashboard](#admin-dashboard)  
- [Usage](#usage)  
- [Contributing](#contributing)  
- [License](#license)  

---

## Features

- Stores transaction history per user  
- Supports multiple transaction statuses (`INITIATED`, `SUCCESS`, `FAILED`, `OTP_REQUIRED`, `BLOCKED`)  
- ML-based risk scoring and fraud detection  
- OTP challenge mechanism for suspicious transactions  
- Analyst dashboard for manual review  
- Historical and aggregated features for ML model training  

---

## Tech Stack

- **Backend:** Python 3.x, Django 4.x  
- **Database:** MySQL (via XAMPP)  
- **Machine Learning:** Python (scikit-learn / custom models)  
- **Admin Dashboard:** Django Admin  
- **APIs:** Django REST Framework (future integration with dummy payment app)  

---

## Architecture

Dummy Payment App → Argus Transaction API → Transaction Model
↓ ↓
OTP Service Fraud Engine / ML Model
↓ ↓
User verification Risk Score / Decision
↓ ↓
Transaction Status Updated → Admin Dashboard / Logs

- **User Model:** Stores basic user info, phone, and block status  
- **Transaction Model:** Stores all payment attempts, risk score, device info, OTP info, and timestamps  
- **Fraud Engine:** Generates risk score, decides OTP requirement or blocking  
- **OTP Service:** Sends OTP via SMS or email, verifies responses  
- **Admin Dashboard:** Allows analysts to filter, search, and review transactions  

---

## Setup

1. Clone repository:

```bash
git clone <repo-url>
cd argus-transaction-monitor
```

2. Create virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4.Configure MySQL database in settings.py:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'argus_db',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

5. Apply migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

6. Create superuser for admin:
```bash
python manage.py createsuperuser
```

7.Run server:

```bash
python manage.py runserver
```

## Access Admin Dashboard
Open in your browser: 
  http://127.0.0.1:8000/admin


---

## Database Models

### User
| Field       | Type         | Notes           |
|------------|-------------|----------------|
| user_id    | CharField    | Unique         |
| phone      | CharField    |                |
| is_blocked | BooleanField | Default: False |
| created_at | DateTimeField| Auto-generated |

### Transaction
| Field           | Type         | Notes                                      |
|----------------|-------------|-------------------------------------------|
| txn_id         | CharField    | Unique                                     |
| user           | ForeignKey   | Links to User                              |
| amount         | Decimal/Float | Transaction amount                         |
| currency       | CharField    | Currency code (USD, INR, etc.)            |
| status         | CharField    | INITIATED, SUCCESS, FAILED, OTP_REQUIRED, BLOCKED |
| fraud_decision | CharField    | Result from fraud engine                   |
| risk_score     | Float        | Calculated risk score                      |
| device_id      | CharField    | Device identifier                          |
| ip_address     | CharField    | IP address of transaction                  |
| channel        | CharField    | Payment channel                            |
| otp_required   | BooleanField | Indicates if OTP is needed                 |
| otp_verified   | BooleanField | Indicates if OTP was verified              |
| failure_reason | CharField    | Reason for failure, if any                 |
| created_at     | DateTimeField| Auto-generated                             |
| updated_at     | DateTimeField| Auto-updated                               |

---

## Admin Dashboard Features
- Fully searchable and filterable transaction records  
- Filters for `status`, `fraud_decision`, and `created_at`  
- Read-only fields for transaction history  
- Allows analysts to review transactions and block users  

---

## Usage
1. Dummy Payment App sends transaction data to Argus API  
2. Transaction is stored with `INITIATED` status  
3. Fraud Engine evaluates transaction risk  
4. OTP Service is triggered if necessary  
5. Transaction status updated (`SUCCESS`, `FAILED`, `OTP_REQUIRED`, `BLOCKED`)  
6. Admin dashboard shows all transactions for review  
7. ML model uses transaction history for training and feature aggregation  

---




