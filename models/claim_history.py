from datetime import datetime
from . import db

class ClaimHistory(db.Model):
    __tablename__ = "claim_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "actor_name": self.actor.name if self.actor else None,
            "actor_role": self.actor.role if self.actor else None,
            "comment": self.comment,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

