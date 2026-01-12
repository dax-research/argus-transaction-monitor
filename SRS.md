# Software Requirements Specification for Argus Transaction Monitor

## 3.1 External Interface Requirements

### 3.1.1 User Interfaces
The Argus Transaction Monitor provides a web-based interface accessible via standard web browsers (Chrome, Firefox, Edge, Safari). The user interface is designed for two user roles:
1. **Admin**: Has full access to all system features including alert resolution and rule configuration.
2. **Read-only User**: Has view-only access to dashboards and logs but cannot modify data or resolve alerts.

**Main Dashboard Interface:**
*   **Visual Logic:** The dashboard presents a "cockpit" view of the system's status. It features a dark-themed, high-contrast aesthetic suitable for prolonged monitoring.
*   **Key Elements:**
    *   **Navigation Sidebar:** Links to Dashboard, Alerts, Rules Engine, Audit Log, and Settings.
    *   **Real-Time Metrics Cards:** Displays key indices such as "Total Transactions," "Flagged Anomalies," and "Processing Latency."
    *   **Live Charts:** Interactive `Chart.js` visualizations showing transaction volume over time and fraud classification ratios.
    *   **Recent Alerts Feed:** A scrolling list of the most recent high-risk transactions requiring immediate attention.
*   **Interaction:** Users interact primarily via mouse (clicking navigation items, hovering over chart data points for details) and keyboard (search fields, data entry). The interface is responsive and adapts to desktop and tablet resolutions.

*(Note: In a full document, a screenshot of the existing Argus Dashboard would be inserted here)*

### 3.1.2 Hardware Interfaces
The system is software-centric but relies on standard server and client hardware.

*   **Server Hardware:**
    *   The application backend is designed to run on scalable cloud compute instances (e.g., AWS EC2, Google Compute Engine) or on-premise servers.
    *   Requires sufficient RAM and CPU to support the Dockerized environment containing Django, Redis, and the Celery workers.
*   **Client Hardware:**
    *   Users access the system via standard workstations (PC/Mac) or laptops.
    *   No specialized sensors or proprietary hardware peripherals are required.
*   **Network:**
    *   Requires a high-bandwidth, low-latency broadband internet connection to handle real-time transaction streams and WebSocket updates.

### 3.1.3 Software Interfaces
The Argus system interacts with several external and internal software components:

*   **Transaction Data Sources:** The system exposes a RESTful API to ingest data from external banking cores or payment gateways (e.g., SWIFT simulation, internal ledger systems).
*   **Database Server:** Interfaces with **PostgreSQL** for persistent storage of transaction records, user profiles, and audit logs.
*   **Message Broker:** Dispatches asynchronous tasks to **Redis** for the Celery workers to process ML inference jobs.
*   **Machine Learning Libraries:** Integrates with `scikit-learn` and `pandas` for the Isolation Forest model execution.

## 3.2 Functional Requirements

### 3.2.1 F1: Transaction Ingestion
The system shall accept financial transaction records (including amount, currency, source account, destination account, timestamp) via a secure HTTP POST API endpoint.

### 3.2.2 F2: Rule-Based Validation
The system shall validate every incoming transaction against a configurable set of deterministic rules, including:
*   **Velocity Checks:** Flagging accounts with >N transactions in M minutes.
*   **Threshold Checks:** Flagging transactions exceeding a defined monetary value.
*   **Watchlist Checks:** Flagging transactions involving blacklisted account numbers.

### 3.2.3 F3: ML Anomaly Detection
The system shall process transactions through an Isolation Forest machine learning model to assign an "Anomaly Score" (0.0 to 1.0). Transactions with a score exceeding the defined sensitivity threshold shall be marked as "Suspicious."

### 3.2.4 F4: Real-Time Dashboard Updates
The system shall update the frontend dashboard visuals in near real-time (latency < 5 seconds) to reflect new transactions and alerts without requiring a full page reload.

### 3.2.5 F5: Alert Management
The system shall generate a unique Alert entity for any transaction flagged by either the Rule-Based engine or the ML engine. These alerts must be viewable in the "Alerts" view and track the review status (Open, Investigating, Resolved).

## 3.3 Use Case Model

```mermaid
usecaseDiagram
    actor "Admin" as Admin
    actor "Read-only User" as Reader
    actor "External Banking System" as Bank

    package "Argus System" {
        usecase "Ingest Transaction Stream" as UC1
        usecase "Monitor Dashboard" as UC2
        usecase "Review Function" as UC3
        usecase "Configure Risk Rules" as UC4
    }

    Bank --> UC1
    Admin --> UC2
    Admin --> UC3
    Admin --> UC4
    Reader --> UC2
```

### 3.3.1 Use Case #1: Review Suspicious Transaction (UC3)

*   **Author:** Argus Development Team
*   **Purpose:** To investigate a transaction flagged by the system and determine if it is genuine fraud or a false positive.
*   **Requirements Traceability:** F2, F3, F5
*   **Priority:** High
*   **Preconditions:**
    1.  The Admin is logged into the system.
    2.  At least one transaction has been flagged as "Suspicious" by the engine.
*   **Post conditions:**
    1.  The Alert status is updated to "Resolved".
    2.  An audit log entry is created recording the Admin's decision.
*   **Actors:** Admin
*   **Extends:** None
*   **Flow of Events:**
    1.  **Basic Flow:**
        1.  Admin navigates to the "Alerts" page.
        2.  System displays a list of open alerts sorted by severity.
        3.  Admin clicks on a specific alert ID.
        4.  System displays detailed transaction metadata, anomaly score, and reason for flagging.
        5.  Admin reviews the data (potentially checking external records).
        6.  Admin clicks "Mark as Fraud" or "Mark as Safe".
        7.  System saves the decision and removes the alert from the "Open" queue.
    2.  **Alternative Flow:**
        *   If the specific alert has already been claimed by another Admin, the system locks the review to prevent duplicate work.
    3.  **Exceptions:**
        *   Database connection failure: System displays an error message and retains the alert state.
*   **Notes/Issues:** Need to define the retention policy for closed alerts in the future.

### 3.3.2 Use Case #2: Ingest Transaction Stream (UC1)

*   **Author:** Argus Development Team
*   **Purpose:** To receive and process high-volume financial data from external sources for monitoring.
*   **Requirements Traceability:** F1, F2, F3
*   **Priority:** Critical
*   **Preconditions:**
    1.  The Argus API server is running and accessible.
    2.  The Redis message broker is operational.
*   **Post conditions:**
    1.  The transaction is saved to the PostgreSQL database.
    2.  An async task is queued for fraud analysis.
*   **Actors:** External Banking System
*   **Extends:** None
*   **Flow of Events:**
    1.  **Basic Flow:**
        1.  External Banking System sends a JSON payload containing transaction details to the `/api/ingest/` endpoint.
        2.  System validates the JSON schema (checks for required fields).
        3.  System saves the raw transaction with status "Pending".
        4.  System pushes the transaction ID to the Celery task queue.
        5.  System returns HTTP 201 Created response to the External Banking System.
    2.  **Alternative Flow:**
        *   **Validation Failure:** If JSON is malformed, System returns HTTP 400 Bad Request.
    3.  **Exceptions:**
        *   **Database Outage:** System returns HTTP 503 Service Unavailable if it cannot write the initial record.
*   **Notes/Issues:** Current throughput limit is tested at 500 transactions/second.
