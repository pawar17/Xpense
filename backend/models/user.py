from datetime import datetime
from bson import ObjectId

class User:
    def __init__(self, db):
        self.collection = db.users
        self._create_indexes()

    def _create_indexes(self):
        """Create indexes for better query performance"""
        self.collection.create_index("username", unique=True)
        self.collection.create_index("email", unique=True)

    def create_user(self, username, email, password_hash, name, country="USA", state="", tax_bracket=0):
        """Create a new user"""
        user = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "country": country,
            "state": state,
            "currency_code": "USD",
            "tax_bracket": tax_bracket,
            "nessie_customer_id": None,
            "nessie_account_ids": [],
            "game_points": 0,
            "game_currency": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "last_activity_date": datetime.utcnow(),
            "friends": [],
            "veto_authorized_friends": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.collection.insert_one(user)
        return result.inserted_id

    def find_by_username(self, username):
        """Find user by username"""
        return self.collection.find_one({"username": username})

    def find_by_email(self, email):
        """Find user by email"""
        return self.collection.find_one({"email": email})

    def find_by_id(self, user_id):
        """Find user by ID"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        return self.collection.find_one({"_id": user_id})

    def update_user(self, user_id, update_data):
        """Update user data"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        update_data["updated_at"] = datetime.utcnow()
        return self.collection.update_one(
            {"_id": user_id},
            {"$set": update_data}
        )

    def update_game_stats(self, user_id, points=0, currency=0, streak=None):
        """Update game statistics"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        update = {
            "$inc": {
                "game_points": points,
                "game_currency": currency
            },
            "$set": {
                "updated_at": datetime.utcnow()
            }
        }

        if streak is not None:
            update["$set"]["current_streak"] = streak
            update["$set"]["last_activity_date"] = datetime.utcnow()

        return self.collection.update_one({"_id": user_id}, update)

    def add_friend(self, user_id, friend_id):
        """Add friend to user's friend list"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        if isinstance(friend_id, str):
            friend_id = ObjectId(friend_id)

        return self.collection.update_one(
            {"_id": user_id},
            {"$addToSet": {"friends": friend_id}}
        )

    def get_leaderboard(self, limit=100):
        """Get top users by points"""
        return list(self.collection.find(
            {},
            {"username": 1, "name": 1, "game_points": 1, "current_streak": 1}
        ).sort("game_points", -1).limit(limit))
