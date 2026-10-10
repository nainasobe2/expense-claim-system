from models import db, ClaimHistory

def log_claim_action(claim_id: int, actor_id: int, action: str, comment: str = None) -> ClaimHistory:
    """
    Creates an immutable audit log entry in the claim_history table.
    """
    entry = ClaimHistory(
        claim_id=claim_id,
        actor_id=actor_id,
        action=action,
        comment=comment
    )
    db.session.add(entry)
    db.session.commit()
    return entry

