# Project Brief: Smart Expense Claim Approval System

- **Problem ID:** PS-068
- **Project Name:** Smart Expense Claim Approval System
- **Team Name:** The Semicolons

---

## 1. Problem Statement
Organizations routinely process significant volumes of employee expense claims across categories such as travel, meals, equipment, supplies, and miscellaneous expenses. Manual checking of these claims is error-prone, labor-intensive, and consistently misses duplicate submissions, policy non-compliance, and invalid claims.

The goal is to build an automated **Smart Expense Claim Approval System** that validates claims in real-time, proactively flags policy violations and duplicate submissions against historical records, and dynamically routes claims through role-based approval pipelines while maintaining a tamper-evident audit trail.

---

## 2. Core Workflow
1. **Submission:** Employee submits an expense claim with essential details (amount, category, expense date, description) and receipt attachment.
2. **Automated Policy Validation:** The system validates amount limits, category constraints, submission deadlines / date boundaries, and required attachments.
3. **Duplicate & Anomaly Detection:** Claim details are checked against historical claims (same employee/vendor, exact amount match, date proximity, duplicate receipt hash/content) to flag potential duplicates.
4. **Approval Routing:** Based on policy rules (e.g., amount thresholds, department hierarchy, violation flags), the claim is routed to the appropriate approver (Manager / Approver) and subsequently to Finance/Admin.
5. **Decision & Audit Trail:** Approver reviews, approves, requests clarification, or rejects the claim with comments. Every state transition and action is logged in an immutable audit trail.
6. **Analytics & Status Tracking:** Final status is recorded; real-time tracking is provided for employees and consolidated spend analytics for Finance/Admin.

---

## 3. Technology Stack (Strict Requirements)
* **Frontend:** Plain HTML5, CSS3, Vanilla JavaScript (Strictly **no** React, Vue, or heavy front-end frameworks).
* **Backend:** Python Flask, RESTful API architecture.
* **Database:** MySQL (using `mysql-connector-python` or `SQLAlchemy`).
* **OCR (Stretch Feature):** Tesseract OCR (`pytesseract`) for automated receipt text & field extraction (built last).

---

## 4. User Roles & Access Control
1. **Employee:**
   - Submit new expense claims with receipt uploads.
   - View real-time status and historical claims with policy feedback/flags.
   - View timeline/audit progress of submitted claims.

2. **Approver / Manager:**
   - Review pending claims assigned to their team/department.
   - Inspect receipt, system-flagged policy violations, and duplicate risk scores.
   - Approve, reject, or request revision with mandatory review notes.

3. **Finance / Admin:**
   - High-level oversight across all claims and department budgets.
   - Final disbursement approval / settlement.
   - System policy configuration (category limits, allowable date ranges).
   - Spend analytics and comprehensive audit log inspection.

---

## 5. Key Features (6 Pillars)
1. **Smart Claim Submission Form:**
   - Responsive, intuitive form capturing amount, currency, category, date, business purpose, and receipt file upload.
   - Client-side validation for instant feedback.

2. **Automated Policy Validation Engine:**
   - Verifies category-specific caps (e.g., Meals max $50, Travel max $500 without pre-approval).
   - Validates date validity (e.g., claims must be submitted within 30 days of expense date; no future dates).
   - Flags out-of-policy claims with specific reason codes before or during submission.

3. **Duplicate Detection Engine:**
   - Matches incoming claims against claim history using multi-factor heuristics:
     - Exact duplicate check (same user, amount, date, category).
     - Fuzzy duplicate check (same amount, vendor/description within ±3 days across same team/user).
     - File checksum / perceptual hash duplicate receipt detection.
   - Assigns a duplicate risk score and highlights suspicious items to approvers.

4. **Approval Workflow Routing:**
   - Dynamic routing engine:
     - Standard claims under threshold & no violations $\rightarrow$ Single-level Manager approval.
     - High-value claims or claims with policy/duplicate flags $\rightarrow$ Escalated multi-level approval (Manager + Finance).
   - Status transitions: `DRAFT`, `SUBMITTED`, `PENDING_MANAGER`, `PENDING_FINANCE`, `APPROVED`, `REJECTED`, `REVISION_REQUESTED`.

5. **Claim History & Immutable Audit Trail:**
   - Detailed event log recording every action: timestamp, actor, action, previous state, new state, comments, and IP/metadata.
   - Visual timeline displayed on claim detail view.

6. **OCR Receipt Extraction (Stretch Feature):**
   - Integration with Tesseract OCR (`pytesseract`).
   - Extracts merchant name, total amount, and transaction date from uploaded receipt images/PDFs.
   - Auto-populates submission form fields with confidence flags for user verification.

---

## 6. System Architecture (3-Tier)
1. **User Layer (Presentation):**
   - Clean, accessible role-based web interface built with semantic HTML, modern CSS (Flexbox/Grid), and modular vanilla JavaScript.
   - Communicates asynchronously via Fetch API with JSON payloads.

2. **Application Layer (Business Logic & Services):**
   - **Flask Application:** RESTful endpoints for Auth, Claims, Approvals, Policies, and Analytics.
   - **Validation Engine:** Rule evaluation modular service.
   - **Duplicate Detection Service:** Historical query analyzer & hash matcher.
   - **Workflow Engine:** State machine handling claim transitions and routing logic.
   - **OCR Extraction Service:** Background/synchronous image processing via Tesseract.

3. **Data Layer (Persistence & Analytics):**
   - **MySQL Database:** Normalized relational schema covering Users, Roles, Claims, Claim Items, Receipts, Policies, Audit Logs, and Approvals.
   - Spend analytics queries and indexed lookups for duplicate heuristics.

