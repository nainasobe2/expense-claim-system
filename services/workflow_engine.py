from typing import Dict, Any, Tuple
from models import db, Claim, User
from services.audit_service import log_claim_action

HIGH_VALUE_THRESHOLD = 250.00

def requires_finance_escalation(amount: float, flags: list) -> bool:
    """
    Returns True if the claim exceeds the high-value threshold
    OR contains any policy violations / duplicate flags.
    """
    has_flags = bool(flags and len(flags) > 0)
    is_high_value = float(amount or 0) > HIGH_VALUE_THRESHOLD
    return is_high_value or has_flags

def process_claim_decision(
    claim_id: int,
    actor: User,
    action: str,
    comment: str = ""
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Processes an approval or rejection decision adhering to routing rules:
    
    1. Rejection:
       - Either Manager or Finance can reject -> Claim status becomes 'REJECTED'.
       
    2. Manager Approval:
       - If clean and under $250 -> Transitions directly to 'APPROVED'.
       - If high-value (> $250) or flagged -> Transitions to 'PENDING_FINANCE' with escalation note.
       
    3. Finance Approval:
       - Moves claim from 'PENDING_FINANCE' to 'APPROVED'.
       
    Every transition logs an immutable entry to claim_history.
    """
    claim = Claim.query.get(claim_id)
    if not claim:
        return False, f"Claim #{claim_id} not found.", {}

    action = action.upper().strip()
    comment = (comment or "").strip()

    if action not in ["APPROVE", "REJECT"]:
        return False, f"Invalid action '{action}'. Must be 'APPROVE' or 'REJECT'.", {}

    # -------------------------------------------------------------------------
    # Rejection Handling
    # -------------------------------------------------------------------------
    if action == "REJECT":
        if not comment:
            return False, "A rejection reason/comment is mandatory.", {}

        prev_status = claim.status
        claim.status = "REJECTED"
        db.session.commit()

        audit_action = f"{actor.role}_REJECTED"
        audit_note = f"Claim rejected by {actor.name} ({actor.role}). Reason: {comment}"
        log_claim_action(
            claim_id=claim.id,
            actor_id=actor.id,
            action=audit_action,
            comment=audit_note
        )

        return True, f"Claim #{claim.id} has been rejected.", claim.to_dict()

    # -------------------------------------------------------------------------
    # Approval Handling
    # -------------------------------------------------------------------------
    if action == "APPROVE":
        # MANAGER Approval Path
        if actor.role in ["MANAGER", "FINANCE_ADMIN"] and claim.status == "PENDING_MANAGER":
            needs_finance = requires_finance_escalation(claim.amount, claim.flags)

            if needs_finance:
                # Escalated to Finance
                claim.status = "PENDING_FINANCE"
                # Assign to Finance Admin
                finance_user = User.query.filter_by(role="FINANCE_ADMIN").first()
                if finance_user:
                    claim.assigned_approver_id = finance_user.id
                db.session.commit()

                escalation_reasons = []
                if float(claim.amount) > HIGH_VALUE_THRESHOLD:
                    escalation_reasons.append(f"High-value claim (${float(claim.amount):,.2f} > ${HIGH_VALUE_THRESHOLD:,.2f})")
                if claim.flags:
                    escalation_reasons.append(f"{len(claim.flags)} warning/duplicate flag(s)")
                
                reason_str = ", ".join(escalation_reasons)
                audit_note = f"Approved by Manager {actor.name}. Escalated to Finance due to: {reason_str}."
                if comment:
                    audit_note += f" Note: {comment}"

                log_claim_action(
                    claim_id=claim.id,
                    actor_id=actor.id,
                    action="MANAGER_APPROVED_ESCALATED",
                    comment=audit_note
                )

                return True, f"Claim #{claim.id} approved by Manager and routed to Finance for final sign-off.", claim.to_dict()
            else:
                # Clean claim under threshold -> Final approval
                claim.status = "APPROVED"
                db.session.commit()

                audit_note = f"Approved by Manager {actor.name}. Fully cleared (clean claim under threshold)."
                if comment:
                    audit_note += f" Note: {comment}"

                log_claim_action(
                    claim_id=claim.id,
                    actor_id=actor.id,
                    action="MANAGER_APPROVED_FINAL",
                    comment=audit_note
                )

                return True, f"Claim #{claim.id} fully approved.", claim.to_dict()

        # FINANCE Approval Path
        elif actor.role == "FINANCE_ADMIN" and claim.status == "PENDING_FINANCE":
            claim.status = "APPROVED"
            db.session.commit()

            audit_note = f"Final approval & disbursement sign-off by Finance {actor.name}."
            if comment:
                audit_note += f" Note: {comment}"

            log_claim_action(
                claim_id=claim.id,
                actor_id=actor.id,
                action="FINANCE_APPROVED_FINAL",
                comment=audit_note
            )

            return True, f"Claim #{claim.id} approved by Finance.", claim.to_dict()

        else:
            return False, f"Action not permitted. Claim status '{claim.status}' cannot be approved by {actor.role}.", {}

    return False, "Unknown action.", {}

