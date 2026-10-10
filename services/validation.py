from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional
from models import Policy

def validate_claim(
    amount: float,
    category: str,
    expense_date: date,
    has_receipt: bool,
    policy: Optional[Policy] = None
) -> Tuple[bool, List[Dict[str, str]]]:
    """
    Validates an expense claim against organizational policies.
    Checks:
      1. amount > 0 and within category limit
      2. category is valid
      3. date is not in the future and not older than the allowed window
      4. receipt is attached when required
      
    Returns:
      (is_valid, list_of_violations)
      Where each violation is a dict:
        {"type": str, "message": str, "severity": "LOW" | "MEDIUM" | "HIGH"}
    """
    violations: List[Dict[str, str]] = []
    today = date.today()

    # 1. Basic amount validation
    if amount is None or amount <= 0:
        violations.append({
            "type": "INVALID_AMOUNT",
            "message": "Claim amount must be greater than $0.00.",
            "severity": "HIGH"
        })

    # 2. Category validation & policy lookup
    normalized_category = (category or "").strip().upper()
    if not policy and normalized_category:
        policy = Policy.query.filter_by(category=normalized_category).first()

    if not policy:
        violations.append({
            "type": "INVALID_CATEGORY",
            "message": f"Expense category '{category}' is not recognized in active policies.",
            "severity": "HIGH"
        })
    else:
        # Check category maximum amount limit
        max_amt = float(policy.max_amount)
        if amount is not None and amount > max_amt:
            violations.append({
                "type": "LIMIT_EXCEEDED",
                "message": f"Claim amount (${amount:,.2f}) exceeds the {policy.category} maximum limit of ${max_amt:,.2f}.",
                "severity": "HIGH"
            })

        # 3. Date boundary validations
        if expense_date:
            if expense_date > today:
                violations.append({
                    "type": "FUTURE_DATE",
                    "message": f"Expense date ({expense_date.isoformat()}) cannot be in the future.",
                    "severity": "HIGH"
                })
            else:
                max_age_days = policy.max_days_old
                oldest_allowed = today - timedelta(days=max_age_days)
                if expense_date < oldest_allowed:
                    days_ago = (today - expense_date).days
                    violations.append({
                        "type": "DATE_EXPIRED",
                        "message": f"Expense date is {days_ago} days old, which exceeds the allowable limit of {max_age_days} days for {policy.category}.",
                        "severity": "MEDIUM"
                    })

        # 4. Receipt requirement check
        receipt_threshold = float(policy.receipt_required_above)
        if amount is not None and amount > receipt_threshold and not has_receipt:
            violations.append({
                "type": "RECEIPT_REQUIRED",
                "message": f"Receipt attachment is mandatory for {policy.category} claims over ${receipt_threshold:,.2f}.",
                "severity": "HIGH"
            })

    is_clean = len(violations) == 0
    return is_clean, violations

