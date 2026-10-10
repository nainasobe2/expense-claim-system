import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_full_flow():
    s = requests.Session()

    print("=== STEP 1: LOGIN AS EMPLOYEE ===")
    res = s.post(f"{BASE_URL}/api/auth/login", json={"email": "employee@example.com", "password": "password123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    print("Logged in as Alice:", res.json()["user"]["name"])

    print("\n=== STEP 2: SUBMIT A VALID CLAIM ===")
    res_valid = s.post(f"{BASE_URL}/api/claims", data={
        "category": "MEALS",
        "amount": "18.50",
        "expense_date": "2026-10-09",
        "description": "Team morning coffee standup discussion"
    })
    assert res_valid.status_code == 201, f"Submit valid failed: {res_valid.text}"
    valid_claim = res_valid.json()["claim"]
    print(f"Valid Claim #{valid_claim['id']} submitted: Amount=${valid_claim['amount']}, Clean={res_valid.json()['is_clean']}, Status={valid_claim['status']}")
    assert res_valid.json()["is_clean"] == True

    print("\n=== STEP 3: SUBMIT A POLICY-VIOLATING CLAIM (MEALS > $75 CAP) ===")
    res_violation = s.post(f"{BASE_URL}/api/claims", data={
        "category": "MEALS",
        "amount": "95.00",
        "expense_date": "2026-10-09",
        "description": "Client dinner at Seafood Grill exceeding policy cap"
    })
    assert res_violation.status_code == 201, f"Submit violation failed: {res_violation.text}"
    viol_claim = res_violation.json()["claim"]
    print(f"Policy-Violating Claim #{viol_claim['id']} submitted: Clean={res_violation.json()['is_clean']}, Flags count={len(viol_claim['flags'])}")
    assert res_violation.json()["is_clean"] == False
    assert any(f["type"] == "LIMIT_EXCEEDED" for f in viol_claim["flags"])

    print("\n=== STEP 4: SUBMIT A DUPLICATE CLAIM (MATCHING CLAIM #5 RECEIPT) ===")
    with open("uploads/receipt_standing_desk.png", "rb") as f:
        res_dup = s.post(f"{BASE_URL}/api/claims", data={
            "category": "EQUIPMENT",
            "amount": "420.00",
            "expense_date": "2026-10-09",
            "description": "Duplicate submission of desk converter"
        }, files={"receipt": ("receipt_standing_desk.png", f, "image/png")})
    assert res_dup.status_code == 201, f"Submit duplicate failed: {res_dup.text}"
    dup_claim = res_dup.json()["claim"]
    print(f"Duplicate Claim #{dup_claim['id']} submitted: Flags={json.dumps(dup_claim['flags'])}")
    dup_flag = next((f for f in dup_claim["flags"] if f.get("rule") == "RECEIPT_HASH_MATCH"), None)
    assert dup_flag is not None
    print(f"Matched duplicate to Claim #{dup_flag['matched_claim_id']}")

    s.get(f"{BASE_URL}/api/auth/logout")

    print("\n=== STEP 5: LOGIN AS BOB MANAGER & REVIEW QUEUE ===")
    res_mgr = s.post(f"{BASE_URL}/api/auth/login", json={"email": "manager@example.com", "password": "password123"})
    assert res_mgr.status_code == 200
    print("Logged in as Manager:", res_mgr.json()["user"]["name"])

    queue_res = s.get(f"{BASE_URL}/api/approvals/queue")
    assert queue_res.status_code == 200
    queue = queue_res.json()
    print(f"Manager Queue has {len(queue)} pending claims")

    print("\n=== STEP 6: APPROVE VALID CLAIM (Direct Final Approval) ===")
    app_res = s.post(f"{BASE_URL}/api/approvals/{valid_claim['id']}/action", json={
        "action": "APPROVE",
        "comment": "Approved - within policy limits."
    })
    assert app_res.status_code == 200
    print(f"Valid claim #{valid_claim['id']} approval status:", app_res.json()["claim"]["status"])
    assert app_res.json()["claim"]["status"] == "APPROVED"

    print("\n=== STEP 7: APPROVE POLICY-VIOLATING CLAIM (Escalation to Finance) ===")
    app_res2 = s.post(f"{BASE_URL}/api/approvals/{viol_claim['id']}/action", json={
        "action": "APPROVE",
        "comment": "Manager exception granted for business necessity; routing to Finance."
    })
    assert app_res2.status_code == 200
    print(f"Violating claim #{viol_claim['id']} approval status:", app_res2.json()["claim"]["status"])
    assert app_res2.json()["claim"]["status"] == "PENDING_FINANCE"

    print("\n=== STEP 8: REJECT DUPLICATE CLAIM ===")
    rej_res = s.post(f"{BASE_URL}/api/approvals/{dup_claim['id']}/action", json={
        "action": "REJECT",
        "comment": f"Rejected duplicate claim. Identified identical receipt already submitted in Claim #{dup_flag['matched_claim_id']}."
    })
    assert rej_res.status_code == 200
    print(f"Duplicate claim #{dup_claim['id']} rejection status:", rej_res.json()["claim"]["status"])
    assert rej_res.json()["claim"]["status"] == "REJECTED"

    s.get(f"{BASE_URL}/api/auth/logout")

    print("\n=== STEP 9: LOGIN AS CAROL FINANCE & SIGN OFF ===")
    res_fin = s.post(f"{BASE_URL}/api/auth/login", json={"email": "finance@example.com", "password": "password123"})
    assert res_fin.status_code == 200
    print("Logged in as Finance:", res_fin.json()["user"]["name"])

    fin_res = s.post(f"{BASE_URL}/api/finance/{viol_claim['id']}/action", json={
        "action": "APPROVE",
        "comment": "Disbursement approved and cleared by Finance."
    })
    assert fin_res.status_code == 200
    print(f"Violating claim #{viol_claim['id']} finance approval status:", fin_res.json()["claim"]["status"])
    assert fin_res.json()["claim"]["status"] == "APPROVED"

    print("\n=== STEP 10: VERIFY TIMELINE AUDIT HISTORY ===")
    detail_res = s.get(f"{BASE_URL}/api/claims/{viol_claim['id']}")
    assert detail_res.status_code == 200
    history = detail_res.json()["history"]
    print(f"Claim #{viol_claim['id']} audit events ({len(history)}):")
    for h in history:
        print(f"  - [{h['timestamp']}] {h['action']} by {h['actor_name']} ({h['actor_role']}) -> {h['comment']}")

    print("\n>>> COMPLETE END-TO-END FLOW VERIFIED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_full_flow()

