from flask import Blueprint, request, jsonify, session
from models import db, Claim, User
from routes.auth_routes import login_required, role_required
from services.workflow_engine import process_claim_decision, requires_finance_escalation, HIGH_VALUE_THRESHOLD

approval_bp = Blueprint("approvals", __name__)

@approval_bp.route("/api/approvals/queue", methods=["GET"])
@login_required
@role_required("MANAGER", "FINANCE_ADMIN")
def get_approval_queue():
    """
    Returns pending claims awaiting Manager review, enriched with
    flags, duplicate references, and escalation indicators.
    """
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    
    # Fetch claims in PENDING_MANAGER status
    query = Claim.query.filter_by(status="PENDING_MANAGER")

    # If manager has a department, prioritize/filter by their department
    if user.role == "MANAGER" and user.department:
        # Match employee's department with manager's department
        query = query.join(User, Claim.user_id == User.id).filter(User.department == user.department)

    claims = query.order_by(Claim.created_at.desc()).all()

    enriched_claims = []
    for c in claims:
        data = c.to_dict()
        data["requires_finance_escalation"] = requires_finance_escalation(c.amount, c.flags)
        data["high_value_threshold"] = HIGH_VALUE_THRESHOLD
        
        # Check if there are matched duplicate claims to fetch brief comparison info
        duplicate_matches = []
        if c.flags:
            for f in c.flags:
                matched_id = f.get("matched_claim_id")
                if matched_id:
                    matched_claim = Claim.query.get(matched_id)
                    if matched_claim:
                        duplicate_matches.append({
                            "claim_id": matched_claim.id,
                            "employee_name": matched_claim.employee.name if matched_claim.employee else None,
                            "amount": float(matched_claim.amount),
                            "category": matched_claim.category,
                            "expense_date": matched_claim.expense_date.isoformat(),
                            "status": matched_claim.status,
                            "description": matched_claim.description,
                            "receipt_path": matched_claim.receipt_path
                        })
        data["duplicate_matches"] = duplicate_matches
        enriched_claims.append(data)

    return jsonify(enriched_claims), 200

@approval_bp.route("/api/approvals/<int:claim_id>/action", methods=["POST"])
@login_required
@role_required("MANAGER", "FINANCE_ADMIN")
def perform_approval_action(claim_id):
    """
    Approves or rejects a claim in the review queue.
    """
    user_id = session.get("user_id")
    actor = User.query.get(user_id)

    data = request.get_json(silent=True) or {}
    action = data.get("action", "")
    comment = data.get("comment", "")

    success, message, claim_data = process_claim_decision(
        claim_id=claim_id,
        actor=actor,
        action=action,
        comment=comment
    )

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({
        "message": message,
        "claim": claim_data
    }), 200

