from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User
from .policy import Policy
from .claim import Claim
from .claim_history import ClaimHistory

__all__ = ["db", "User", "Policy", "Claim", "ClaimHistory"]

