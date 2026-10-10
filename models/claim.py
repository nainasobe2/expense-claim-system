from datetime import datetime
from . import db

class Claim(db.Model):
    __tablename__ = "claims"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    expense_date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    receipt_path = db.Column(db.String(255), nullable=True)
    receipt_hash = db.Column(db.String(64), nullable=True, index=True)
    status = db.Column(
        db.Enum("SUBMITTED", "PENDING_MANAGER", "PENDING_FINANCE", "APPROVED", "REJECTED", "REVISION_REQUESTED", name="claim_status_enum"),
        nullable=False,
        default="SUBMITTED",
        index=True
    )
    flags = db.Column(db.JSON, nullable=True)
    assigned_approver_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    history = db.relationship("ClaimHistory", backref="claim", cascade="all, delete-orphan", lazy="dynamic", order_by="ClaimHistory.timestamp.desc()")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "employee_name": self.employee.name if self.employee else None,
            "employee_department": self.employee.department if self.employee else None,
            "amount": float(self.amount) if self.amount is not None else 0.0,
            "category": self.category,
            "expense_date": self.expense_date.isoformat() if self.expense_date else None,
            "description": self.description,
            "receipt_path": self.receipt_path,
            "receipt_hash": self.receipt_hash,
            "status": self.status,
            "flags": self.flags or [],
            "assigned_approver_id": self.assigned_approver_id,
            "assigned_approver_name": self.approver.name if self.approver else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

