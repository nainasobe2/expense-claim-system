import unittest
import hashlib
from datetime import date, timedelta
from app import create_app
from models import db, User, Claim, Policy
from services.duplicates import check_duplicates

class TestDuplicateDetection(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Fetch seed users
        self.user1 = User.query.filter_by(email="employee@example.com").first()
        self.user2 = User.query.filter_by(email="manager@example.com").first()

    def tearDown(self):
        # Clean up any test claims created during tests (keeping seed data intact)
        test_claims = Claim.query.filter(Claim.description.like("TEST_%")).all()
        for c in test_claims:
            db.session.delete(c)
        db.session.commit()
        self.ctx.pop()

    def test_resubmitted_receipt_in_different_month(self):
        """
        Scenario: Employee submits a receipt in January.
        Two months later in March, the employee resubmits the exact same receipt
        file for a new claim with different dates and descriptions.
        The duplicate detection engine must catch the identical receipt hash
        and link to the original January claim ID.
        """
        receipt_bytes = b"AIRLINE_BOARDING_PASS_AND_HOTEL_RECEIPT_JANUARY_2026"
        receipt_hash = hashlib.sha256(receipt_bytes).hexdigest()

        # 1. First claim in January
        jan_claim = Claim(
            user_id=self.user1.id,
            amount=420.00,
            category="TRAVEL",
            expense_date=date(2026, 1, 15),
            description="TEST_Client visit in New York City - Flights",
            receipt_path="/uploads/test_jan_flight.pdf",
            receipt_hash=receipt_hash,
            status="APPROVED",
            flags=[]
        )
        db.session.add(jan_claim)
        db.session.commit()
        jan_claim_id = jan_claim.id

        # 2. Resubmission in March (2 months later)
        march_date = date(2026, 3, 20)
        duplicate_flags = check_duplicates(
            user_id=self.user1.id,
            amount=420.00,
            category="TRAVEL",
            expense_date=march_date,
            description="TEST_Quarterly business review travel expense",
            receipt_hash=receipt_hash
        )

        # Assert duplicate was detected
        self.assertGreater(len(duplicate_flags), 0, "Expected duplicate flags for resubmitted receipt.")
        
        # Verify receipt hash match rule and matched claim ID
        hash_match = next((f for f in duplicate_flags if f.get("rule") == "RECEIPT_HASH_MATCH"), None)
        self.assertIsNotNone(hash_match, "Should flag rule RECEIPT_HASH_MATCH")
        self.assertEqual(hash_match["matched_claim_id"], jan_claim_id)
        self.assertEqual(hash_match["severity"], "HIGH")
        self.assertIn(f"Claim #{jan_claim_id}", hash_match["message"])

    def test_resubmitted_receipt_by_different_user(self):
        """
        Scenario: User 1 submits an equipment receipt.
        User 2 later tries to submit the same receipt to claim reimbursement.
        """
        receipt_bytes = b"LAPTOP_MONITOR_RECEIPT_STAPLES_STORE"
        receipt_hash = hashlib.sha256(receipt_bytes).hexdigest()

        orig_claim = Claim(
            user_id=self.user1.id,
            amount=250.00,
            category="EQUIPMENT",
            expense_date=date(2026, 2, 10),
            description="TEST_External 4K Monitor for remote setup",
            receipt_path="/uploads/test_monitor.jpg",
            receipt_hash=receipt_hash,
            status="PENDING_MANAGER",
            flags=[]
        )
        db.session.add(orig_claim)
        db.session.commit()

        # User 2 resubmits same receipt
        flags = check_duplicates(
            user_id=self.user2.id,
            amount=250.00,
            category="EQUIPMENT",
            expense_date=date(2026, 2, 15),
            description="TEST_Purchased monitor for office workstation",
            receipt_hash=receipt_hash
        )

        hash_match = next((f for f in flags if f.get("rule") == "RECEIPT_HASH_MATCH"), None)
        self.assertIsNotNone(hash_match)
        self.assertEqual(hash_match["matched_claim_id"], orig_claim.id)

    def test_amount_and_category_within_close_date_range(self):
        """
        Scenario: Same user submits two claims for the same category and amount
        within a 3-day proximity window without receipts.
        """
        claim_a = Claim(
            user_id=self.user1.id,
            amount=45.00,
            category="MEALS",
            expense_date=date(2026, 10, 1),
            description="TEST_Client lunch meeting at Bistro",
            status="APPROVED",
            flags=[]
        )
        db.session.add(claim_a)
        db.session.commit()

        # 3 days later, identical amount and category submitted
        flags = check_duplicates(
            user_id=self.user1.id,
            amount=45.00,
            category="MEALS",
            expense_date=date(2026, 10, 4),
            description="TEST_Lunch with project partner",
            receipt_hash=None,
            date_window_days=7
        )

        date_match = next((f for f in flags if f.get("rule") == "AMOUNT_CATEGORY_DATE_MATCH"), None)
        self.assertIsNotNone(date_match, "Should flag identical amount & category within 7 days.")
        self.assertEqual(date_match["matched_claim_id"], claim_a.id)
        self.assertEqual(date_match["severity"], "HIGH")

    def test_similar_description_detection(self):
        """
        Scenario: Claims with high description text similarity (>80%).
        """
        claim_desc = Claim(
            user_id=self.user1.id,
            amount=65.00,
            category="TRAVEL",
            expense_date=date(2026, 9, 10),
            description="TEST_Airport taxi fare from JFK to Manhattan Midtown hotel",
            status="APPROVED",
            flags=[]
        )
        db.session.add(claim_desc)
        db.session.commit()

        # Slightly altered wording (>80% similarity)
        flags = check_duplicates(
            user_id=self.user1.id,
            amount=65.00,
            category="TRAVEL",
            expense_date=date(2026, 9, 28), # outside 7-day window so only description matches
            description="TEST_Airport taxi fare from JFK to Manhattan Midtown hotel room",
            receipt_hash=None
        )

        desc_match = next((f for f in flags if f.get("rule") == "DESCRIPTION_SIMILARITY"), None)
        self.assertIsNotNone(desc_match, "Should flag high description similarity.")
        self.assertEqual(desc_match["matched_claim_id"], claim_desc.id)

    def test_legitimate_distinct_claim_not_flagged(self):
        """
        Scenario: Distinct claim with different amount, dates, and receipt hash
        must not trigger false positive duplicate flags.
        """
        flags = check_duplicates(
            user_id=self.user1.id,
            amount=18.50,
            category="MEALS",
            expense_date=date(2026, 5, 20),
            description="TEST_Coffee and pastry for team morning standup",
            receipt_hash="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
        )
        self.assertEqual(len(flags), 0, "Legitimate distinct claims should have 0 duplicate flags.")

if __name__ == "__main__":
    unittest.main()

