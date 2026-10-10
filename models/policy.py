from datetime import datetime
from . import db

class Policy(db.Model):
    __tablename__ = "policies"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(50), unique=True, nullable=False)
    max_amount = db.Column(db.Numeric(10, 2), nullable=False)
    max_days_old = db.Column(db.Integer, nullable=False, default=30)
    receipt_required_above = db.Column(db.Numeric(10, 2), nullable=False, default=25.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "max_amount": float(self.max_amount) if self.max_amount is not None else 0.0,
            "max_days_old": self.max_days_old,
            "receipt_required_above": float(self.receipt_required_above) if self.receipt_required_above is not None else 0.0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

