# 👁️ Argus Monitor: Secure Transaction & Fraud Defense System

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Django](https://img.shields.io/badge/Django-5.0+-green)
![Status](https://img.shields.io/badge/Status-In%20Development-yellow)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## 🌟 Project Overview

**Argus Monitor** is a full-stack, scalable application designed to centralize and process real-time transaction streams. By leveraging asynchronous task queues and a hybrid Machine Learning/Rule-based engine, the system provides a low-latency analytics dashboard for critical fraud defense and compliance monitoring. This project demonstrates proficiency in building robust, data-intensive web services.

Named after **Argus Panoptes**, the all-seeing giant of Greek mythology, the application symbolizes the system's perpetual vigilance over financial transactions.

---

## ✨ Key Features (CV Highlights)

* **Asynchronous Fraud Detection:** Utilizes **Celery** and **Redis** to offload ML analysis and security checks to background workers, ensuring the primary web application remains highly responsive.
* **Hybrid Analysis Engine:** Transactions are screened using a two-layer approach:
    * **Rule-Based:** Implements velocity checks (frequency limits) and regulatory thresholds (e.g., AML compliance).
    * **ML-Based:** Uses the **Isolation Forest** algorithm (`scikit-learn`) for anomaly detection based on user behavior patterns.
* **Secure Ledger Integrity:** Implements **Django's Atomic Transactions** to guarantee data consistency and maintains an immutable **Audit Log** of all critical system events.
* **Real-Time Monitoring Dashboard:** An interactive frontend built with **Chart.js** provides compliance officers with a live feed of transaction volume, fraud ratios, and alerts requiring manual review.

---

## 💻 Tech Stack

| Component | Technology | Role in the System |
| :--- | :--- | :--- |
| **Backend** | Python, Django | Core API, routing, security, and ORM. |
| **Database** | PostgreSQL | Scalable, secure storage for transactions and audit logs. |
| **Asynchronous** | Celery, Redis | Handles non-blocking, time-consuming fraud checks. |
| **ML/Data** | Scikit-learn, Pandas | Fraud detection algorithms and data processing. |
| **Frontend** | HTML, CSS, JavaScript | User interface and dashboard visualization. |

---

## 📸 System Architecture

The following diagram illustrates the flow of a transaction through the secure, decoupled architecture:


> *Note: Transactions are published to the Celery queue upon entry, allowing the system to run complex ML checks asynchronously without blocking the main web server.*

---

## ⚙️ Installation & Setup

Follow these steps to get a local copy of the project running.

### Prerequisites
* Python 3.11+
* PostgreSQL or SQLite
* Redis Server (Required for Celery)

### 1. Clone the Repository
```bash
git clone [https://github.com/](https://github.com/)[YOUR-USERNAME]/argus-transaction-monitor.git
cd argus-transaction-monitor

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate

# Create Superuser (Admin)
python manage.py createsuperuser

python manage.py runserver

# This command starts the process that runs your fraud detection logic
celery -A argus_monitor_project worker -l info


