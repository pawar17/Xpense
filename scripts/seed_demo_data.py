"""
Seed script to create demo data for the hackathon presentation
Run this after setting up MongoDB to populate with demo users, goals, and quests
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from config.database import db_instance
from models.user import User
from models.goal import Goal
from models.side_quest import SideQuest
from utils.auth import hash_password
from datetime import datetime, timedelta

# Connect to database
db = db_instance.connect()

# Initialize models
user_model = User(db)
goal_model = Goal(db)
quest_model = SideQuest(db)

def seed_quest_templates():
    """Create quest templates"""
    print("Seeding quest templates...")

    quests = [
        {
            "name": "No-Spend Challenge",
            "description": "Don't make any purchases for one day",
            "category": "no-spend",
            "points": 50,
            "currency": 25
        },
        {
            "name": "Skip Coffee Run",
            "description": "Make coffee at home instead of buying it",
            "category": "no-spend",
            "points": 30,
            "currency": 15
        },
        {
            "name": "Save Extra $20",
            "description": "Save an additional $20 this week",
            "category": "accelerator",
            "points": 60,
            "currency": 30
        },
        {
            "name": "Brown Bag Lunch",
            "description": "Bring lunch from home for 3 days",
            "category": "no-spend",
            "points": 40,
            "currency": 20
        },
        {
            "name": "Round Up Challenge",
            "description": "Round up every purchase to the nearest $5 and save the difference",
            "category": "accelerator",
            "points": 70,
            "currency": 35
        },
        {
            "name": "Share Your Progress",
            "description": "Post your savings milestone on the social feed",
            "category": "social",
            "points": 25,
            "currency": 10
        },
        {
            "name": "Help a Friend",
            "description": "Send a motivational nudge to a friend",
            "category": "social",
            "points": 20,
            "currency": 10
        },
        {
            "name": "Subscription Audit",
            "description": "Review and cancel one unused subscription",
            "category": "milestone",
            "points": 100,
            "currency": 50
        }
    ]

    for quest in quests:
        quest_model.create_quest_template(
            name=quest["name"],
            description=quest["description"],
            category=quest["category"],
            points_reward=quest["points"],
            currency_reward=quest["currency"],
            verification_type="manual",
            duration_hours=48
        )

    print(f"✓ Created {len(quests)} quest templates")

def seed_demo_users():
    """Create demo users"""
    print("Seeding demo users...")

    demo_users = [
        {
            "username": "alice_saves",
            "email": "alice@demo.com",
            "password": "demo123",
            "name": "Alice Johnson",
            "game_points": 450,
            "game_currency": 230,
            "current_streak": 12
        },
        {
            "username": "bob_budgets",
            "email": "bob@demo.com",
            "password": "demo123",
            "name": "Bob Smith",
            "game_points": 680,
            "game_currency": 150,
            "current_streak": 21
        },
        {
            "username": "carol_goals",
            "email": "carol@demo.com",
            "password": "demo123",
            "name": "Carol Davis",
            "game_points": 320,
            "game_currency": 180,
            "current_streak": 7
        }
    ]

    user_ids = []

    for user_data in demo_users:
        try:
            # Create user
            password_hash = hash_password(user_data["password"])
            user_id = user_model.create_user(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=password_hash,
                name=user_data["name"],
                country="USA",
                state="CA"
            )

            # Update game stats
            user_model.update_game_stats(
                user_id,
                points=user_data["game_points"],
                currency=user_data["game_currency"],
                streak=user_data["current_streak"]
            )

            user_ids.append(user_id)
            print(f"✓ Created user: {user_data['username']}")

        except Exception as e:
            print(f"✗ Failed to create {user_data['username']}: {e}")

    # Make them friends
    if len(user_ids) >= 3:
        user_model.add_friend(user_ids[0], user_ids[1])
        user_model.add_friend(user_ids[0], user_ids[2])
        user_model.add_friend(user_ids[1], user_ids[0])
        user_model.add_friend(user_ids[1], user_ids[2])
        user_model.add_friend(user_ids[2], user_ids[0])
        user_model.add_friend(user_ids[2], user_ids[1])
        print("✓ Created friend connections")

    return user_ids

def seed_demo_goals(user_ids):
    """Create demo goals"""
    print("Seeding demo goals...")

    goals_data = [
        {
            "user_index": 0,
            "goal_name": "Buy a House",
            "category": "house",
            "target_amount": 50000,
            "current_amount": 5000,
            "total_levels": 50,
            "current_level": 5
        },
        {
            "user_index": 1,
            "goal_name": "Vacation to Hawaii",
            "category": "vacation",
            "target_amount": 3000,
            "current_amount": 1500,
            "total_levels": 30,
            "current_level": 15
        },
        {
            "user_index": 2,
            "goal_name": "Pay Off Credit Card",
            "category": "debt",
            "target_amount": 2000,
            "current_amount": 1800,
            "total_levels": 20,
            "current_level": 18
        }
    ]

    for goal_data in goals_data:
        try:
            user_id = user_ids[goal_data["user_index"]]

            # Create goal
            goal_id = goal_model.create_goal(
                user_id=user_id,
                goal_name=goal_data["goal_name"],
                goal_category=goal_data["category"],
                target_amount=goal_data["target_amount"],
                target_date=datetime.utcnow() + timedelta(days=180)
            )

            # Update with demo data
            amount_per_level = goal_data["target_amount"] / goal_data["total_levels"]
            level_thresholds = [
                amount_per_level * i for i in range(1, goal_data["total_levels"] + 1)
            ]

            goal_model.set_level_system(
                goal_id,
                goal_data["total_levels"],
                level_thresholds,
                daily_target=round(goal_data["target_amount"] / 180, 2)
            )

            # Set current progress
            goal_model.contribute(goal_id, goal_data["current_amount"])

            print(f"✓ Created goal: {goal_data['goal_name']}")

        except Exception as e:
            print(f"✗ Failed to create goal: {e}")

def main():
    """Run all seed functions"""
    print("\n=== Seeding Demo Data ===\n")

    try:
        # Seed quest templates first
        seed_quest_templates()

        # Seed demo users
        user_ids = seed_demo_users()

        # Seed demo goals
        if user_ids:
            seed_demo_goals(user_ids)

        print("\n✓ Demo data seeded successfully!")
        print("\nDemo Login Credentials:")
        print("Username: alice_saves | Password: demo123")
        print("Username: bob_budgets | Password: demo123")
        print("Username: carol_goals | Password: demo123")

    except Exception as e:
        print(f"\n✗ Error seeding data: {e}")

    finally:
        db_instance.close()

if __name__ == "__main__":
    main()
