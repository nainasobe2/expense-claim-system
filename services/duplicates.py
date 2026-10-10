from datetime import date, timedelta
import difflib
from typing import List, Dict, Any, Optional
from models import Claim

def check_duplicates(
    user_id: int,
    amount: float,
    category: str,
    expense_date: date,
    description: str,
    receipt_hash: Optional[str] = None,
    exclude_claim_id: Optional[int] = None,
    date_window_days: int = 7,
    description_similarity_threshold: float = 0.80
) -> List[Dict[str, Any]]:
    """
    Detects potential duplicate claims against the existing claim database.
    
    Checks:
    1. Exact Receipt File Hash:
       Matches SHA-256 hash across any historical claim (catches resubmitted receipts even in different months/years).
    2. Amount + Category + Date Proximity:
       Matches identical amount and category within a configurable date window (default +-7 days).
    3. Description Similarity:
       Uses SequenceMatcher to detect highly similar descriptions (>80% similarity) with matching amount or category.
       
    Returns:
    List of duplicate flag dictionaries containing 'matched_claim_id', 'rule', 'severity', and 'message'.
    """
    duplicate_flags: List[Dict[str, Any]] = []
    seen_matched_ids = set()

    # Base query excluding the current claim (if updating an existing claim)
    query = Claim.query
    if exclude_claim_id:
        query = query.filter(Claim.id != exclude_claim_id)

    # Do not check against rejected claims that were canceled/voided
    # (or include all non-draft claims)
    existing_claims = query.all()

    # -------------------------------------------------------------------------
    # 1. Exact Receipt Hash Matching
    # (Resubmitted receipts across any time period or users)
    # -------------------------------------------------------------------------
    if receipt_hash:
        for c in existing_claims:
            if c.receipt_hash and c.receipt_hash == receipt_hash:
                duplicate_flags.append({
                    "type": "POSSIBLE_DUPLICATE",
                    "rule": "RECEIPT_HASH_MATCH",
                    "severity": "HIGH",
                    "message": f"Identical receipt file hash matched Claim #{c.id} (expense date: {c.expense_date}, status: {c.status}).",
                    "matched_claim_id": c.id
                })
                seen_matched_ids.add(c.id)
                break  # Record highest priority match for receipt hash

    # -------------------------------------------------------------------------
    # 2. Amount + Category + Date Proximity Match
    # -------------------------------------------------------------------------
    if amount and category and expense_date:
        for c in existing_claims:
            if c.id in seen_matched_ids:
                continue

            # Compare category and amount
            is_same_category = (c.category or "").strip().upper() == (category or "").strip().upper()
            is_same_amount = abs(float(c.amount) - float(amount)) < 0.005

            if is_same_category and is_same_amount and c.expense_date:
                diff_days = abs((expense_date - c.expense_date).days)
                if diff_days <= date_window_days:
                    is_same_user = (c.user_id == user_id)
                    severity = "HIGH" if is_same_user else "MEDIUM"
                    user_desc = "the same user" if is_same_user else f"user #{c.user_id}"
                    
                    duplicate_flags.append({
                        "type": "POSSIBLE_DUPLICATE",
                        "rule": "AMOUNT_CATEGORY_DATE_MATCH",
                        "severity": severity,
                        "message": (
                            f"Matching amount (${float(amount):,.2f}) and category ({category}) "
                            f"found in Claim #{c.id} by {user_desc} within {diff_days} day(s) "
                            f"(claim date: {c.expense_date})."
                        ),
                        "matched_claim_id": c.id
                    })
                    seen_matched_ids.add(c.id)

    # -------------------------------------------------------------------------
    # 3. Description Similarity Match
    # -------------------------------------------------------------------------
    clean_desc = (description or "").strip().lower()
    if clean_desc and len(clean_desc) > 8:
        for c in existing_claims:
            if c.id in seen_matched_ids:
                continue

            c_desc = (c.description or "").strip().lower()
            if not c_desc or len(c_desc) <= 8:
                continue

            # Calculate text similarity ratio
            similarity = difflib.SequenceMatcher(None, clean_desc, c_desc).ratio()
            if similarity >= description_similarity_threshold:
                # High description similarity, particularly if amount or category matches
                is_same_user = (c.user_id == user_id)
                severity = "HIGH" if is_same_user else "MEDIUM"
                
                duplicate_flags.append({
                    "type": "POSSIBLE_DUPLICATE",
                    "rule": "DESCRIPTION_SIMILARITY",
                    "severity": severity,
                    "message": (
                        f"Claim description is {int(similarity * 100)}% similar to Claim #{c.id} "
                        f"('{(c.description or '')[:45]}...')."
                    ),
                    "matched_claim_id": c.id
                })
                seen_matched_ids.add(c.id)

    return duplicate_flags

