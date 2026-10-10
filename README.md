# Smart Expense Claim Approval System
**Hackathon Problem ID:** PS-068  
**Team Name:** The Semicolons  

A full-stack, enterprise-grade automated expense validation, duplicate detection, and workflow approval system built with Python Flask, MySQL, vanilla HTML5/CSS3/JavaScript, and Tesseract OCR.

---

## 📸 System Screenshots

### 1. Sign In & One-Click Role Switcher
![Login Screen](screenshots/01_login_page.png)
*Role-based portal entry with one-click demo login buttons for Alice (Employee), Bob (Manager), and Carol (Finance).*

### 2. Employee Dashboard & Live Policy Checking
![Employee Portal](screenshots/02_employee_dashboard.png)
*Live submission form with real-time policy evaluation, receipt upload, status metrics, and claims tracking table.*

### 3. Manager / Approver Review Queue
![Approver Review Dashboard](screenshots/03_approver_dashboard.png)
*Pending queue highlighting policy violations, duplicate match alerts, routing indicators (Routes to Finance), and review actions.*

### 4. Finance Control Center & Spend Analytics
![Finance Analytics Dashboard](screenshots/04_finance_dashboard.png)
*Organization master log with status/category/flag filters, disbursement sign-off queue, and real-time category spend analytics.*

### 5. Claim Record & Immutable Audit Trail Timeline
![Claim Detail & Audit Timeline](screenshots/05_claim_detail_timeline.png)
*Full lifecycle tracking of claim submissions, policy warnings, duplicate matches, manager escalation notes, and final finance sign-offs.*

---

## 🌟 6 Core Features Implemented

1. **Smart Claim Submission Form:**
   - Multi-field submission: Amount, category, date, business purpose, and receipt file upload.
   - Real-time client-side and server-side compliance validation.
2. **Policy Validation Engine (`services/validation.py`):**
   - Category spend ceilings (e.g. Meals max $75, Equipment max $500, Travel max $1,000).
   - Date boundary validation (prevents future dates; enforces max allowable receipt age).
   - Enforces receipt attachment above category threshold (e.g. Meals over $20 require receipt).
3. **Duplicate Detection Engine (`services/duplicates.py`):**
   - **Exact Receipt Hash (SHA-256):** Detects identical receipts resubmitted months later or by other employees.
   - **Amount + Category + Date Proximity:** Matches identical claims within $\pm 7$ days.
   - **Description Text Similarity:** Uses `SequenceMatcher` to flag $\ge 80\%$ similar descriptions.
4. **Approval Workflow Routing (`services/workflow_engine.py`):**
   - **Clean claims $\le \$250$:** Manager approval immediately finalizes the claim (`APPROVED`).
   - **High-value claims ($> \$250$) OR Flagged claims:** Automatically routed to Manager with warnings $\rightarrow$ on Manager sign-off, escalated to Finance (`PENDING_FINANCE`) for secondary approval.
   - **Rejections:** Require mandatory comments and immediately terminate the workflow.
5. **Claim History & Immutable Audit Trail (`services/audit_service.py`):**
   - Every mutation (submission, escalation, manager approval, finance approval, rejection) writes a timestamped record to `claim_history`.
   - Rendered as an interactive visual lifecycle timeline on `/claims/<id>`.
6. **Tesseract OCR Receipt Extraction (`services/ocr_service.py`):**
   - Automatically pre-processes receipt images (resizing, grayscale, contrast enhancement).
   - Uses `pytesseract` to parse total amount, transaction date, and infer category/merchant.
   - Auto-fills the submission form while allowing full user review and manual edits.
   - Gracefully flags low-confidence reads ($< 40\%$) with fallback notice for manual entry.

---

## 🛠️ Technology Stack (Strict)

* **Frontend:** Plain HTML5, CSS3, Vanilla JavaScript (zero React/Vue/external frameworks).
* **Backend:** Python 3.9+, Flask REST API.
* **Database:** MySQL 8.0+ / 26+ (`mysql-connector-python`, `PyMySQL`, `Flask-SQLAlchemy`).
* **OCR Engine:** Tesseract OCR 5.5+ (`pytesseract`, `Pillow`).

---

## 👥 Seed User Roles (Default Demo Credentials)

All demo accounts use password: **`password123`**

| Role | Name | Email | Department | Default Portal |
| :--- | :--- | :--- | :--- | :--- |
| **Employee** | Alice Employee | `employee@example.com` | Engineering | `/employee` |
| **Employee** | David Marketing | `david@example.com` | Marketing | `/employee` |
| **Manager** | Bob Manager | `manager@example.com` | Engineering | `/approver` |
| **Manager** | Sarah Director | `sarah@example.com` | Marketing | `/approver` |
| **Finance / Admin** | Carol Finance | `finance@example.com` | Finance | `/finance` |

---

## ⚙️ Setup & Installation Instructions

### 1. Prerequisites
- **Python 3.9+**
- **MySQL Server** (running locally on port 3306 or configured via remote host)
- **Tesseract OCR** (installed via Homebrew on macOS: `brew install tesseract`)

### 2. Environment Configuration
Clone the repository and set up a Python virtual environment:

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create or adjust your `.env` file:

```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=semicolons-smart-expense-secret-key-2026

DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=expense_db

DATABASE_URL=mysql+pymysql://root:@127.0.0.1:3306/expense_db

UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
```

### 3. Initialize Database & Seed Demo Data
Ensure MySQL is running, then create the schema and populate realistic demo records:

```bash
# Method A: Direct SQL import
mysql -u root < schema.sql

# Method B: Run rich demo seeder with sample receipts & historical claims
python seed_demo_data.py
```

### 4. Run the Flask Web Application
```bash
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 🧪 Running Automated Tests

### 1. Duplicate Detection Unit Tests
Verifies cross-month resubmitted receipts, date proximity, and description similarity:
```bash
python -m unittest tests/test_duplicates.py -v
```

### 2. End-to-End Workflow Integration Test
Executes complete employee submission (clean, policy-violating, duplicate), manager review queue, workflow escalation to finance, and final disbursement sign-off:
```bash
python tests/test_e2e_flow.py
```

---

## 📡 REST API Summary

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Authenticate user & establish session | No |
| `GET` | `/api/auth/me` | Fetch currently logged-in user profile | Session |
| `GET` | `/api/auth/logout` | Terminate session | Session |
| `GET` | `/api/policies` | Retrieve active policy categories and caps | No |
| `POST` | `/api/claims/validate` | Real-time inline policy validation | Employee/Session |
| `POST` | `/api/ocr/extract` | Pytesseract OCR extraction on receipt image | Employee/Session |
| `POST` | `/api/claims` | Submit new claim (with receipt & duplicate checks) | Employee |
| `GET` | `/api/claims/my` | Retrieve claims submitted by current employee | Employee |
| `GET` | `/api/claims/<id>` | Full claim detail with complete audit history | Role-based |
| `GET` | `/api/approvals/queue` | Retrieve pending claims for manager's team | Manager / Finance |
| `POST` | `/api/approvals/<id>/action` | Manager decision (`APPROVE` / `REJECT`) | Manager / Finance |
| `GET` | `/api/finance/overview` | Organization claims with filters & spend analytics | Finance Admin |
| `POST` | `/api/finance/<id>/action` | Finance disbursement approval / rejection | Finance Admin |
