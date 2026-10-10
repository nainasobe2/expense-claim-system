import os
import hashlib
from datetime import datetime, date
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, session, current_app
from models import db, Claim, Policy, User
from routes.auth_routes import login_required
from services.validation import validate_claim
from services.duplicates import check_duplicates
from services.audit_service import log_claim_action
from services.ocr_service import extract_receipt_data

claim_bp = Blueprint("claims", __name__)

@claim_bp.route("/api/ocr/extract", methods=["POST"])
@login_required
def ocr_extract_receipt():
    """
    Parses an uploaded receipt image with Tesseract OCR to automatically extract
    amount, date, and category with confidence ratings and manual fallback indicators.
    """
    receipt_file = request.files.get("receipt")
    if not receipt_file or not receipt_file.filename:
        return jsonify({"error": "No receipt file uploaded for OCR."}), 400

    filename = secure_filename(receipt_file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    # Save temporarily into uploads/
    temp_name = f"ocr_temp_{session.get('user_id')}_{int(datetime.utcnow().timestamp())}_{filename}"
    temp_path = os.path.join(current_app.config["UPLOAD_FOLDER"], temp_name)
    receipt_file.save(temp_path)

    try:
        ocr_result = extract_receipt_data(temp_path)
        # Include temp file reference so frontend can keep it if desired
        ocr_result["temp_file"] = temp_name
        return jsonify(ocr_result), 200
    except Exception as err:
        return jsonify({
            "extracted": {"amount": None, "date": None, "category": None},
            "confidence": {"overall": 0.0, "level": "LOW"},
            "low_confidence": True,
            "message": f"OCR processing encountered an issue: {str(err)}. Falling back to manual entry."
        }), 200

@claim_bp.route("/api/policies", methods=["GET"])
def get_policies():
    """
    Returns list of all active spending policies for client-side forms and validation.
    """
    policies = Policy.query.order_by(Policy.category).all()
    return jsonify([p.to_dict() for p in policies]), 200

@claim_bp.route("/api/claims/validate", methods=["POST"])
@login_required
def validate_claim_inline():
    """
    Real-time policy validation endpoint for instant inline feedback.
    Does not persist claim to database.
    """
    data = request.get_json(silent=True) or {}
    category = data.get("category", "").strip().upper()
    has_receipt = bool(data.get("has_receipt", False))

    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0.0

    expense_date = None
    date_str = data.get("expense_date", "")
    if date_str:
        try:
            expense_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({
                "is_clean": False,
                "violations": [{"type": "INVALID_DATE_FORMAT", "message": "Date format must be YYYY-MM-DD.", "severity": "HIGH"}]
            }), 200

    policy = Policy.query.filter_by(category=category).first()
    is_clean, violations = validate_claim(
        amount=amount,
        category=category,
        expense_date=expense_date,
        has_receipt=has_receipt,
        policy=policy
    )

    return jsonify({
        "is_clean": is_clean,
        "violations": violations,
        "policy": policy.to_dict() if policy else None
    }), 200

@claim_bp.route("/api/claims", methods=["POST"])
@login_required
def submit_claim():
    """
    Submits a new expense claim, runs policy validation, calculates receipt hash,
    stores policy violation flags in JSON, assigns manager, and creates audit log.
    """
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User session invalid."}), 401

    if request.is_json:
        data = request.get_json(silent=True) or {}
        receipt_file = None
    else:
        data = request.form
        receipt_file = request.files.get("receipt") if request.files else None

    category = (data.get("category") or "").strip().upper()
    description = (data.get("description") or "").strip()
    date_str = (data.get("expense_date") or "").strip()

    # Parse Amount
    try:
        amount = float(data.get("amount", 0))
        if amount <= 0:
            return jsonify({"error": "Claim amount must be greater than 0."}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount provided."}), 400

    # Parse Date
    if not date_str:
        return jsonify({"error": "Expense date is required."}), 400
    try:
        expense_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Expense date must be in YYYY-MM-DD format."}), 400

    if not description:
        return jsonify({"error": "Business purpose / description is required."}), 400

    # Handle Receipt Upload & SHA-256 Hashing
    receipt_path = None
    receipt_hash = None
    has_receipt = False

    if receipt_file and receipt_file.filename:
        filename = secure_filename(receipt_file.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"png", "jpg", "jpeg", "pdf", "webp"})
        if ext not in allowed:
            return jsonify({"error": f"Invalid file type. Allowed formats: {', '.join(allowed)}"}), 400

        # Read file bytes for SHA-256 hashing (for duplicate detection)
        file_bytes = receipt_file.read()
        receipt_hash = hashlib.sha256(file_bytes).hexdigest()

        # Save to uploads directory
        unique_name = f"claim_{user_id}_{int(datetime.utcnow().timestamp())}_{filename}"
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        save_path = os.path.join(upload_folder, unique_name)
        with open(save_path, "wb") as f:
            f.write(file_bytes)

        receipt_path = f"/uploads/{unique_name}"
        has_receipt = True

    # Run Policy Validation Service
    policy = Policy.query.filter_by(category=category).first()
    is_clean, violations = validate_claim(
        amount=amount,
        category=category,
        expense_date=expense_date,
        has_receipt=has_receipt,
        policy=policy
    )

    # Run Duplicate Detection Service
    duplicate_flags = check_duplicates(
        user_id=user.id,
        amount=amount,
        category=category,
        expense_date=expense_date,
        description=description,
        receipt_hash=receipt_hash
    )

    # Combine all flags
    all_flags = violations + duplicate_flags

    # Assign an approver (Manager from same department or any Manager)
    manager = User.query.filter_by(role="MANAGER", department=user.department).first()
    if not manager:
        manager = User.query.filter_by(role="MANAGER").first()

    assigned_approver_id = manager.id if manager else None

    # Status workflow: initial routing goes to manager
    status = "PENDING_MANAGER"

    # Create Claim
    claim = Claim(
        user_id=user.id,
        amount=amount,
        category=category,
        expense_date=expense_date,
        description=description,
        receipt_path=receipt_path,
        receipt_hash=receipt_hash,
        status=status,
        flags=all_flags,
        assigned_approver_id=assigned_approver_id
    )

    db.session.add(claim)
    db.session.commit()

    # Log initial audit history
    comment_text = f"Claim submitted by {user.name}."
    if all_flags:
        flag_notes = "; ".join([f"[{f.get('type')}] {f.get('message')}" for f in all_flags])
        comment_text += f" Warnings/Flags: {flag_notes}"

    log_claim_action(
        claim_id=claim.id,
        actor_id=user.id,
        action="SUBMITTED",
        comment=comment_text
    )

    return jsonify({
        "message": "Claim submitted successfully.",
        "claim": claim.to_dict(),
        "is_clean": len(all_flags) == 0,
        "violations": violations,
        "duplicate_flags": duplicate_flags,
        "flags": all_flags
    }), 201

@claim_bp.route("/api/claims/my", methods=["GET"])
@login_required
def get_my_claims():
    """
    Returns list of claims submitted by the currently logged-in user.
    """
    user_id = session.get("user_id")
    claims = Claim.query.filter_by(user_id=user_id).order_by(Claim.created_at.desc()).all()
    return jsonify([c.to_dict() for c in claims]), 200

@claim_bp.route("/api/claims/<int:claim_id>", methods=["GET"])
@login_required
def get_claim_detail(claim_id):
    """
    Returns full details for a claim, including audit history.
    """
    user_id = session.get("user_id")
    user_role = session.get("role")

    claim = Claim.query.get_or_404(claim_id)

    # Authorization: only creator, managers, or finance admin can view
    if user_role == "EMPLOYEE" and claim.user_id != user_id:
        return jsonify({"error": "Forbidden."}), 403

    history_entries = [h.to_dict() for h in claim.history.all()]
    claim_data = claim.to_dict()
    claim_data["history"] = history_entries

    return jsonify(claim_data), 200

