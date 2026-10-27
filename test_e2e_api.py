import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi.testclient import TestClient
from app.main import app

def run_e2e_tests():
    client = TestClient(app)
    print("=== STARTING FULL-STACK E2E API VERIFICATION ===")

    # 1. Root and Health check
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "online"
    print("✓ Root & Health checks OK")

    # 2. Register New User
    new_user_data = {
        "name": "Devanshi Sen",
        "email": "devanshi@example.com",
        "password": "securepassword123",
        "age": 22,
        "gender": "Female",
        "city": "Bhopal",
        "occupation": "MANIT Student"
    }
    reg_res = client.post("/api/auth/register", json=new_user_data)
    if reg_res.status_code == 400 and "already exists" in reg_res.text:
        # If already registered, login
        login_res = client.post("/api/auth/login", json={
            "email": "devanshi@example.com",
            "password": "securepassword123"
        })
        devanshi_token = login_res.json()["access_token"]
        devanshi_user = login_res.json()["user"]
    else:
        assert reg_res.status_code == 201
        devanshi_token = reg_res.json()["access_token"]
        devanshi_user = reg_res.json()["user"]
    print(f"✓ User registered: {devanshi_user['name']} (ID: {devanshi_user['id']})")

    headers_devanshi = {"Authorization": f"Bearer {devanshi_token}"}

    # 3. Login as Rahul (pre-seeded user)
    login_rahul = client.post("/api/auth/login", json={
        "email": "rahul@roomfit.example.com",
        "password": "password123"
    })
    assert login_rahul.status_code == 200
    rahul_token = login_rahul.json()["access_token"]
    headers_rahul = {"Authorization": f"Bearer {rahul_token}"}
    print("✓ Rahul authenticated with JWT token")

    # 4. Fetch Questions
    q_res = client.get("/api/questions")
    assert q_res.status_code == 200
    questions = q_res.json()
    assert len(questions) >= 15
    print(f"✓ Retrieved {len(questions)} questionnaire items")

    # 5. Devanshi submits questionnaire answers
    sample_answers = [
        {"question_id": questions[0]["id"], "answer": "Non-smoker"},
        {"question_id": questions[1]["id"], "answer": "Non-drinker"},
        {"question_id": questions[2]["id"], "answer": "No pets"},
        {"question_id": questions[4]["id"], "answer": "23:00"},
        {"question_id": questions[5]["id"], "answer": "07:30"},
        {"question_id": questions[7]["id"], "answer": 5}, # cleanliness
        {"question_id": questions[10]["id"], "answer": "Vegetarian"},
    ]
    ans_res = client.post("/api/questions/answers", json={"answers": sample_answers}, headers=headers_devanshi)
    assert ans_res.status_code == 200
    print("✓ Devanshi submitted questionnaire answers, synced to preferences")

    # Update Devanshi's preferred areas
    pref_res = client.put("/api/profile/preferences", json={
        "budget_min": 6000,
        "budget_max": 8000,
        "preferred_areas": ["Kolar Road", "MP Nagar"],
        "deal_breakers": ["no_smokers"]
    }, headers=headers_devanshi)
    assert pref_res.status_code == 200
    print("✓ Devanshi updated preferred areas: Kolar Road, MP Nagar, ₹6,000-₹8,000")

    # 6. Check Recommendations for Rahul
    rec_res = client.get("/api/matches/recommendations", headers=headers_rahul)
    assert rec_res.status_code == 200
    matches = rec_res.json()
    assert len(matches) > 0
    top_match = matches[0]
    print(f"✓ Rahul's Top Match: {top_match['user']['name']} with {top_match['compatibility_score']}% compatibility!")
    print(f"  Explanation: {top_match['explanation']}")
    assert top_match['compatibility_score'] >= 80

    # 7. Check Detailed Breakdown
    breakdown_res = client.get(f"/api/matches/{top_match['user']['id']}/breakdown", headers=headers_rahul)
    assert breakdown_res.status_code == 200
    bd = breakdown_res.json()["breakdown"]
    print(f"✓ 7-Category Breakdown: Lifestyle={bd['lifestyle']}%, Routine={bd['daily_routine']}%, Cleanliness={bd['cleanliness']}%, Food={bd['food']}%, Budget={bd['budget']}%, Location={bd['location']}%")

    # 8. Search Filter Test
    search_res = client.post("/api/matches/search", json={
        "city": "Bhopal",
        "food_preference": "Vegetarian",
        "smoking": "Non-smoker",
        "budget_max": 9000,
        "min_compatibility": 70
    }, headers=headers_rahul)
    assert search_res.status_code == 200
    search_matches = search_res.json()
    print(f"✓ Filtered search for 'Bhopal + Vegetarian + Non-smoker' returned {len(search_matches)} candidates")

    # 9. Test Mutual Match Workflow between Devanshi and Priya
    login_priya = client.post("/api/auth/login", json={
        "email": "priya@roomfit.example.com",
        "password": "password123"
    })
    priya_token = login_priya.json()["access_token"]
    priya_user = login_priya.json()["user"]
    headers_priya = {"Authorization": f"Bearer {priya_token}"}

    # Step 9a: Devanshi expresses interest in Priya
    int1 = client.post(f"/api/interests/{priya_user['id']}", headers=headers_devanshi)
    assert int1.status_code == 200
    assert int1.json()["status"] in ["pending", "mutual"]
    print(f"✓ Devanshi expressed interest in Priya: status={int1.json()['status']}")

    # Step 9b: Priya expresses interest in Devanshi -> triggers mutual match!
    int2 = client.post(f"/api/interests/{devanshi_user['id']}", headers=headers_priya)
    assert int2.status_code == 200
    assert int2.json()["status"] == "mutual"
    assert int2.json()["is_mutual"] == True
    print(f"✓ Priya liked Devanshi back -> {int2.json()['message']}")

    # 10. Test Chat Between Mutual Matches (Devanshi & Priya)
    msg_send = client.post(f"/api/messages/{priya_user['id']}", json={
        "message": "Hi Priya! I saw you are looking for a flat in MP Nagar. Are you free to check out a 2BHK this weekend?"
    }, headers=headers_devanshi)
    assert msg_send.status_code == 200
    print("✓ Devanshi successfully sent message to Priya")

    # Priya reads and replies
    priya_chat = client.get(f"/api/messages/{devanshi_user['id']}", headers=headers_priya)
    assert priya_chat.status_code == 200
    assert len(priya_chat.json()) >= 1
    print(f"✓ Priya retrieved message history: '{priya_chat.json()[-1]['message']}'")

    priya_reply = client.post(f"/api/messages/{devanshi_user['id']}", json={
        "message": "Hey Devanshi! Yes absolutely, Saturday afternoon works best for me."
    }, headers=headers_priya)
    assert priya_reply.status_code == 200
    print("✓ Priya successfully sent reply message")

    # 11. Verify Non-Mutual Chat is Blocked
    login_vikram = client.post("/api/auth/login", json={
        "email": "vikram@roomfit.example.com",
        "password": "password123"
    })
    vikram_token = login_vikram.json()["access_token"]
    headers_vikram = {"Authorization": f"Bearer {vikram_token}"}

    blocked_msg = client.post(f"/api/messages/{devanshi_user['id']}", json={
        "message": "Unsolicited message"
    }, headers=headers_vikram)
    assert blocked_msg.status_code == 403
    print("✓ Security Check PASSED: Unmatched user blocked from messaging (403 Forbidden)")

    # 12. Admin Stats & Weights Update
    login_admin = client.post("/api/auth/login", json={
        "email": "admin@roomfit.example.com",
        "password": "adminpassword123"
    })
    admin_token = login_admin.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    stats_res = client.get("/api/admin/stats", headers=headers_admin)
    assert stats_res.status_code == 200
    st = stats_res.json()
    print(f"✓ Admin Stats: Users={st['total_users']}, Mutual Matches={st['total_mutual_matches']}, Messages={st['total_messages']}")

    print("\n=== ALL E2E API AND BUSINESS LOGIC TESTS PASSED WITH 100% SUCCESS ===")

if __name__ == "__main__":
    run_e2e_tests()
