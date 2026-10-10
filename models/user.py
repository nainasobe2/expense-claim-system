from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("EMPLOYEE", "MANAGER", "FINANCE_ADMIN", name="user_role_enum"), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    claims = db.relationship("Claim", foreign_keys="Claim.user_id", backref="employee", lazy=True)
    assigned_claims = db.relationship("Claim", foreign_keys="Claim.assigned_approver_id", backref="approver", lazy=True)
    history_actions = db.relationship("ClaimHistory", backref="actor", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "department": self.department,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

