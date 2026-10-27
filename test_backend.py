import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine, SessionLocal
from app.models import User, Preference, Question, Answer, Interest, Message
from app.seed import seed_database
from app.compatibility import (
    calculate_compatibility,
    calculate_time_score,
    calculate_budget_score,
    check_deal_breakers
)
from app.auth import get_password_hash, verify_password, create_access_token

def test_compatibility_algorithm():
    print("\n--- TEST 1: Compatibility Algorithm ---")
    
    # 1. Time scoring tests
    t_close = calculate_time_score("23:00", "23:30")
    print(f"Time score for 23:00 vs 23:30: {t_close}% (Expected >= 90%)")
    assert t_close >= 90, f"Expected >= 90, got {t_close}"
    
    t_far = calculate_time_score("22:00", "03:00")
    print(f"Time score for 22:00 vs 03:00: {t_far}% (Expected <= 40%)")
    assert t_far <= 40, f"Expected <= 40, got {t_far}"
    
    # 2. Budget scoring tests
    b_overlap = calculate_budget_score(6000, 8000, 7000, 9000)
    print(f"Budget score for [6k-8k] vs [7k-9k]: {b_overlap}% (Expected >= 80%)")
    assert b_overlap >= 80, f"Expected >= 80, got {b_overlap}"
    
    b_far = calculate_budget_score(4000, 5000, 10000, 15000)
    print(f"Budget score for [4k-5k] vs [10k-15k]: {b_far}% (Expected <= 30%)")
    assert b_far <= 30, f"Expected <= 30, got {b_far}"
    
    # 3. Deal breaker tests
    u1 = {"name": "A", "city": "Bhopal", "gender": "Male"}
    p1 = {"smoking": "Non-smoker", "deal_breakers": ["no_smokers"]}
    u2 = {"name": "B", "city": "Bhopal", "gender": "Male"}
    p2 = {"smoking": "Regular", "deal_breakers": []}
    
    violated, reasons = check_deal_breakers(u1, p1, u2, p2)
    print(f"Deal breaker triggered for non-smoker vs regular smoker: {violated} - {reasons}")
    assert violated == True
    
    # Overall score with deal breaker
    res = calculate_compatibility(u1, p1, u2, p2)
    print(f"Overall score with deal-breaker violation: {res['overall_score']}% (Capped <= 25%)")
    assert res['overall_score'] <= 25
    assert res['is_deal_breaker_violated'] == True

    # 4. High compatibility match test
    u_rahul = {"name": "Rahul", "city": "Bhopal", "gender": "Male", "age": 23}
    p_rahul = {
        "budget_min": 6000, "budget_max": 8000,
        "preferred_areas": ["Kolar Road", "MP Nagar"],
        "room_type": "Private room", "smoking": "Non-smoker",
        "drinking": "Non-drinker", "pets": "No pets",
        "food_preference": "Vegetarian", "cooks": "Sometimes",
        "sleep_time": "23:00", "wake_time": "07:30",
        "cleanliness": 4, "guest_preference": "Sometimes",
        "social_preference": "Balanced", "work_style": "Office / College",
        "deal_breakers": ["no_smokers"]
    }
    
    u_aman = {"name": "Aman", "city": "Bhopal", "gender": "Male", "age": 24}
    p_aman = {
        "budget_min": 6500, "budget_max": 8500,
        "preferred_areas": ["Kolar Road", "Arera Colony"],
        "room_type": "Private room", "smoking": "Non-smoker",
        "drinking": "Non-drinker", "pets": "No pets",
        "food_preference": "Vegetarian", "cooks": "Sometimes",
        "sleep_time": "23:30", "wake_time": "07:30",
        "cleanliness": 5, "guest_preference": "Rarely",
        "social_preference": "Quiet", "work_style": "Office / College",
        "deal_breakers": ["no_smokers"]
    }
    
    res_high = calculate_compatibility(u_rahul, p_rahul, u_aman, p_aman)
    print(f"Compatibility between Rahul and Aman: {res_high['overall_score']}%")
    print(f"Breakdown: {res_high['breakdown']}")
    print(f"Explanation: {res_high['explanation']}")
    assert res_high['overall_score'] >= 85, f"Expected >= 85, got {res_high['overall_score']}"
    print("PASSED TEST 1")

def test_database_and_endpoints():
    print("\n--- TEST 2: Database Initialization, Seeding & Lifecycle ---")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
        
        users_count = db.query(User).count()
        questions_count = db.query(Question).count()
        print(f"Seeded Users count: {users_count}")
        print(f"Seeded Questions count: {questions_count}")
        assert users_count >= 8
        assert questions_count >= 15
        
        # Test password hashing
        rahul = db.query(User).filter(User.email == "rahul@roomfit.example.com").first()
        assert rahul is not None
        assert verify_password("password123", rahul.password_hash) == True
        print(f"User {rahul.name} authenticated successfully with hashed password.")
        
        # Test mutual match
        aman = db.query(User).filter(User.email == "aman@roomfit.example.com").first()
        assert aman is not None
        
        mutual_interest = db.query(Interest).filter(
            Interest.sender_id == rahul.id,
            Interest.receiver_id == aman.id,
            Interest.status == "mutual"
        ).first()
        assert mutual_interest is not None
        print(f"Mutual match between Rahul and Aman verified in database.")
        
        # Test messages
        messages = db.query(Message).filter(
            ((Message.sender_id == rahul.id) & (Message.receiver_id == aman.id)) |
            ((Message.sender_id == aman.id) & (Message.receiver_id == rahul.id))
        ).all()
        print(f"Found {len(messages)} messages between Rahul and Aman.")
        assert len(messages) >= 2
        
        print("PASSED TEST 2")
    finally:
        db.close()

if __name__ == "__main__":
    test_compatibility_algorithm()
    test_database_and_endpoints()
    print("\nALL BACKEND TESTS PASSED SUCCESSFULLY! Ready for production deployment.")
