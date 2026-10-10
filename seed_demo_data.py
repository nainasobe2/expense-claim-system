import os
import hashlib
from datetime import date, timedelta
from PIL import Image, ImageDraw
from app import create_app
from models import db, User, Policy, Claim, ClaimHistory

def generate_sample_receipt(filename: str, title: str, amount_str: str, date_str: str, category: str) -> str:
    upload_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    img = Image.new("RGB", (700, 480), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    text = f"""=====================================
          {title.upper()}
=====================================
Date: {date_str}
Category: {category}
Reference #: INV-{hashlib.md5(filename.encode()).hexdigest()[:8].upper()}

Description: Business expense item
Item Cost:                  ${amount_str}
Tax & Processing:           $0.00
-------------------------------------
TOTAL AMOUNT:               ${amount_str}
=====================================
Status: PAID IN FULL (VISA ending 4128)
Thank you for your business!
"""
    draw.text((30, 30), text, fill=(20, 20, 20))
    img.save(filepath)
    return filepath

def seed():
    app = create_app()
    with app.app_context():
        print("Clearing existing claims and history...")
        ClaimHistory.query.delete()
        Claim.query.delete()
        db.session.commit()

        # 1. Users
        users_data = [
            ("Alice Employee", "employee@example.com", "EMPLOYEE", "Engineering"),
            ("David Marketing", "david@example.com", "EMPLOYEE", "Marketing"),
            ("Bob Manager", "manager@example.com", "MANAGER", "Engineering"),
            ("Sarah Director", "sarah@example.com", "MANAGER", "Marketing"),
            ("Carol Finance", "finance@example.com", "FINANCE_ADMIN", "Finance"),
        ]

        users = {}
        for name, email, role, dept in users_data:
            u = User.query.filter_by(email=email).first()
            if not u:
                u = User(name=name, email=email, role=role, department=dept)
                u.set_password("password123")
                db.session.add(u)
            else:
                u.name = name
                u.department = dept
                u.role = role
                u.set_password("password123")
            users[email] = u
        db.session.commit()

        # Refresh users dict with IDs
        for email in list(users.keys()):
            users[email] = User.query.filter_by(email=email).first()

        alice = users["employee@example.com"]
        david = users["david@example.com"]
        bob = users["manager@example.com"]
        sarah = users["sarah@example.com"]
        carol = users["finance@example.com"]

        # 2. Policies
        policies_data = [
            ("TRAVEL", 1000.00, 30, 50.00),
            ("MEALS", 75.00, 15, 20.00),
            ("EQUIPMENT", 500.00, 45, 100.00),
            ("OTHER", 150.00, 30, 25.00)
        ]
        for cat, max_amt, max_days, receipt_above in policies_data:
            p = Policy.query.filter_by(category=cat).first()
            if not p:
                p = Policy(category=cat, max_amount=max_amt, max_days_old=max_days, receipt_required_above=receipt_above)
                db.session.add(p)
            else:
                p.max_amount = max_amt
                p.max_days_old = max_days
                p.receipt_required_above = receipt_above
        db.session.commit()

        today = date.today()

        # Generate sample receipt images
        r1_path = generate_sample_receipt("receipt_bistro_lunch.png", "Bistro Cafe Downtown", "42.50", (today - timedelta(days=5)).isoformat(), "MEALS")
        r2_path = generate_sample_receipt("receipt_flight_summit.png", "United Airlines Flights", "850.00", (today - timedelta(days=8)).isoformat(), "TRAVEL")
        r3_path = generate_sample_receipt("receipt_team_dinner.png", "Prime Steakhouse", "110.00", (today - timedelta(days=2)).isoformat(), "MEALS")
        r4_path = generate_sample_receipt("receipt_standing_desk.png", "Staples Office Solutions", "420.00", (today - timedelta(days=4)).isoformat(), "EQUIPMENT")

        with open(r1_path, "rb") as f: r1_hash = hashlib.sha256(f.read()).hexdigest()
        with open(r2_path, "rb") as f: r2_hash = hashlib.sha256(f.read()).hexdigest()
        with open(r3_path, "rb") as f: r3_hash = hashlib.sha256(f.read()).hexdigest()
        with open(r4_path, "rb") as f: r4_hash = hashlib.sha256(f.read()).hexdigest()

        # 3. Create Diverse Claims

        # Claim 1: Fully Approved Clean Meal Claim ($42.50)
        c1 = Claim(
            user_id=alice.id,
            amount=42.50,
            category="MEALS",
            expense_date=today - timedelta(days=5),
            description="Lunch with cloud vendor technical account representative",
            receipt_path="/uploads/receipt_bistro_lunch.png",
            receipt_hash=r1_hash,
            status="APPROVED",
            flags=[],
            assigned_approver_id=bob.id
        )
        db.session.add(c1)
        db.session.commit()
        db.session.add(ClaimHistory(claim_id=c1.id, actor_id=alice.id, action="SUBMITTED", comment="Claim submitted by Alice Employee."))
        db.session.add(ClaimHistory(claim_id=c1.id, actor_id=bob.id, action="MANAGER_APPROVED_FINAL", comment="Approved by Manager Bob Manager. Fully cleared (clean claim under threshold)."))
        db.session.commit()

        # Claim 2: Fully Approved High-Value Travel Claim ($850.00)
        c2 = Claim(
            user_id=alice.id,
            amount=850.00,
            category="TRAVEL",
            expense_date=today - timedelta(days=8),
            description="Roundtrip flights and airport transit for Q3 Developer Summit",
            receipt_path="/uploads/receipt_flight_summit.png",
            receipt_hash=r2_hash,
            status="APPROVED",
            flags=[],
            assigned_approver_id=carol.id
        )
        db.session.add(c2)
        db.session.commit()
        db.session.add(ClaimHistory(claim_id=c2.id, actor_id=alice.id, action="SUBMITTED", comment="Claim submitted by Alice Employee."))
        db.session.add(ClaimHistory(claim_id=c2.id, actor_id=bob.id, action="MANAGER_APPROVED_ESCALATED", comment="Approved by Manager Bob Manager. Escalated to Finance due to: High-value claim ($850.00 > $250.00)."))
        db.session.add(ClaimHistory(claim_id=c2.id, actor_id=carol.id, action="FINANCE_APPROVED_FINAL", comment="Final approval & disbursement sign-off by Finance Carol Finance."))
        db.session.commit()

        # Claim 3: Clean Claim Awaiting Manager Review ($65.00)
        c3 = Claim(
            user_id=alice.id,
            amount=65.00,
            category="MEALS",
            expense_date=today - timedelta(days=1),
            description="Working dinner with engineering team during sprint crunch",
            receipt_path=None,
            receipt_hash=None,
            status="PENDING_MANAGER",
            flags=[],
            assigned_approver_id=bob.id
        )
        db.session.add(c3)
        db.session.commit()
        db.session.add(ClaimHistory(claim_id=c3.id, actor_id=alice.id, action="SUBMITTED", comment="Claim submitted by Alice Employee."))
        db.session.commit()

        # Claim 4: Flagged Claim Exceeding Policy Cap ($110.00 Meals > $75)
        c4 = Claim(
            user_id=alice.id,
            amount=110.00,
            category="MEALS",
            expense_date=today - timedelta(days=2),
            description="Client executive dinner at Prime Steakhouse",
            receipt_path="/uploads/receipt_team_dinner.png",
            receipt_hash=r3_hash,
            status="PENDING_MANAGER",
            flags=[{
                "type": "LIMIT_EXCEEDED",
                "message": "Claim amount ($110.00) exceeds the MEALS maximum limit of $75.00.",
                "severity": "HIGH"
            }],
            assigned_approver_id=bob.id
        )
        db.session.add(c4)
        db.session.commit()
        db.session.add(ClaimHistory(claim_id=c4.id, actor_id=alice.id, action="SUBMITTED", comment="Claim submitted by Alice Employee. Warnings/Flags: [LIMIT_EXCEEDED] Claim amount ($110.00) exceeds MEALS limit."))
        db.session.commit()

        # Claim 5: High-Value Equipment Awaiting Finance Sign-off ($420.00)
        c5 = Claim(
            user_id=david.id,
            amount=420.00,
            category="EQUIPMENT",
            expense_date=today - timedelta(days=4),
            description="Ergonomic dual-monitor sit-stand desk converter for workstation",
            receipt_path="/uploads/receipt_standing_desk.png",
            receipt_hash=r4_hash,
            status="PENDING_FINANCE",
            flags=[],
            assigned_approver_id=carol.id
        )
        db.session.add(c5)
        db.session.commit()
        db.session.add(ClaimHistory(claim_id=c5.id, actor_id=david.id, action="SUBMITTED", comment="Claim submitted by David Marketing."))
        db.session.add(ClaimHistory(claim_id=c5.id, actor_id=sarah.id, action="MANAGER_APPROVED_ESCALATED", comment="Approved by Manager Sarah Director. Escalated to Finance due to: High-value claim ($420.00 > $250.00)."))
        db.session.commit()

        # Claim 6: Duplicate Claim Flagged (Same Receipt Hash as Claim 5)
        c6 = Claim(
            user_id=alice.id,
            amount=420.00,
            category="EQUIPMENT",
            expense_date=today - timedelta(days=1),
            description="Dual-monitor standing desk converter for home office",
            receipt_path="/uploads/receipt_standing_desk.png",
            receipt_hash=r4_hash,
            status="PENDING_MANAGER",
            flags=[{
                "type": "POSSIBLE_DUPLICATE",
                "rule": "RECEIPT_HASH_MATCH",
                "severity": "HIGH",
                "message": f"Identical receipt file hash matched Claim #{c5.id} (expense date: {c5.expense_date}, status: {c5.status}).",
                "matched_claim_id": c5.id
            }],
            assigned_approver_id=bob.id
        )
        db.session.add(c6)
        db.session.commit()
        db.session.add(ClaimHistory(claim_id=c6.id, actor_id=alice.id, action="SUBMITTED", comment=f"Claim submitted by Alice Employee. Warnings/Flags: [POSSIBLE_DUPLICATE] Identical receipt file hash matched Claim #{c5.id}."))
        db.session.commit()

        # Claim 7: Rejected Out-of-Policy Claim ($180.00)
        c7 = Claim(
            user_id=alice.id,
            amount=180.00,
            category="OTHER",
            expense_date=today - timedelta(days=12),
            description="Wireless noise-canceling headphones for personal commute",
            receipt_path=None,
            receipt_hash=None,
            status="REJECTED",
            flags=[{
                "type": "LIMIT_EXCEEDED",
                "message": "Claim amount ($180.00) exceeds the OTHER maximum limit of $150.00.",
                "severity": "HIGH"
            }],
            assigned_approver_id=bob.id
        )
        db.session.add(c7)
        db.session.commit()
        db.session.add(ClaimHistory(claim_id=c7.id, actor_id=alice.id, action="SUBMITTED", comment="Claim submitted by Alice Employee. Warnings/Flags: [LIMIT_EXCEEDED] Claim amount exceeds $150.00."))
        db.session.add(ClaimHistory(claim_id=c7.id, actor_id=bob.id, action="MANAGER_REJECTED", comment="Claim rejected by Bob Manager (MANAGER). Reason: Personal commute audio accessories are non-reimbursable under corporate travel & expense policy."))
        db.session.commit()

        print(f"Demo data seeded successfully!")
        print(f"Users: {User.query.count()} | Policies: {Policy.query.count()} | Claims: {Claim.query.count()} | History: {ClaimHistory.query.count()}")

if __name__ == "__main__":
    seed()

