from flask import Blueprint, request, jsonify, session
from sqlalchemy import func
from models import db, Claim, User, Policy
from routes.auth_routes import login_required, role_required
from services.workflow_engine import process_claim_decision

finance_bp = Blueprint("finance", __name__)

@finance_bp.route("/api/finance/overview", methods=["GET"])
@login_required
@role_required("FINANCE_ADMIN")
def get_finance_overview():
    """
    Returns filtered company-wide claims along with spend analytics:
    - Totals by category (approved spend)
    - Flagged claims count & rate
    - Pending disbursement queue
    """
    status_filter = request.args.get("status", "ALL").strip().upper()
    category_filter = request.args.get("category", "ALL").strip().upper()
    flagged_filter = request.args.get("flagged", "ALL").strip().upper()

    query = Claim.query

    # Apply Status Filter
    if status_filter != "ALL":
        query = query.filter(Claim.status == status_filter)

    # Apply Category Filter
    if category_filter != "ALL":
        query = query.filter(Claim.category == category_filter)

    claims = query.order_by(Claim.created_at.desc()).all()

    # Apply Flagged in-memory filter if specified
    if flagged_filter == "FLAGGED_ONLY":
        filtered_claims = [c for c in claims if c.flags and len(c.flags) > 0]
    elif flagged_filter == "CLEAN_ONLY":
        filtered_claims = [c for c in claims if not c.flags or len(c.flags) == 0]
    else:
        filtered_claims = claims

    # -------------------------------------------------------------------------
    # Spend Analytics Aggregations (across all company claims)
    # -------------------------------------------------------------------------
    all_company_claims = Claim.query.all()
    
    total_approved_spend = 0.0
    pending_disbursement_count = 0
    pending_disbursement_amount = 0.0
    flagged_count = 0
    total_claims_count = len(all_company_claims)

    # Category totals for approved claims
    categories = [p.category for p in Policy.query.all()] or ["TRAVEL", "MEALS", "EQUIPMENT", "OTHER"]
    category_spend = {cat: 0.0 for cat in categories}
    category_counts = {cat: 0 for cat in categories}

    for c in all_company_claims:
        amt = float(c.amount or 0)
        cat = (c.category or "OTHER").upper()
        if cat not in category_spend:
            category_spend[cat] = 0.0
            category_counts[cat] = 0

        category_counts[cat] += 1

        if c.status == "APPROVED":
            total_approved_spend += amt
            category_spend[cat] += amt

        if c.status == "PENDING_FINANCE":
            pending_disbursement_count += 1
            pending_disbursement_amount += amt

        if c.flags and len(c.flags) > 0:
            flagged_count += 1

    flag_rate = round((flagged_count / total_claims_count * 100), 1) if total_claims_count > 0 else 0.0

    return jsonify({
        "claims": [c.to_dict() for c in filtered_claims],
        "analytics": {
            "total_approved_spend": round(total_approved_spend, 2),
            "pending_disbursement_count": pending_disbursement_count,
            "pending_disbursement_amount": round(pending_disbursement_amount, 2),
            "flagged_claims_count": flagged_count,
            "total_claims_count": total_claims_count,
            "flag_rate_percent": flag_rate,
            "category_spend": {k: round(v, 2) for k, v in category_spend.items()},
            "category_counts": category_counts
        }
    }), 200

@finance_bp.route("/api/finance/<int:claim_id>/action", methods=["POST"])
@login_required
@role_required("FINANCE_ADMIN")
def perform_finance_action(claim_id):
    """
    Finance Admin approval or rejection for disbursement.
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

