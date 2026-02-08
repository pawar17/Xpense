from datetime import datetime, timedelta
from bson import ObjectId

class SideQuest:
    def __init__(self, db):
        self.collection = db.side_quests
        self.user_quests = db.user_quests
        self._create_indexes()

    def _create_indexes(self):
        """Create indexes"""
        self.collection.create_index("quest_category")
        self.user_quests.create_index([("user_id", 1), ("status", 1)])

    def create_quest_template(self, name, description, category, points_reward, currency_reward,
                             verification_type="manual", duration_hours=24, requirements=None):
        """Create a quest template"""
        quest = {
            "quest_name": name,
            "quest_description": description,
            "quest_category": category,  # milestone, no-spend, accelerator, social
            "points_reward": points_reward,
            "currency_reward": currency_reward,
            "verification_type": verification_type,  # manual, automatic
            "duration_hours": duration_hours,
            "requirements": requirements or {},
            "is_active": True
        }
        result = self.collection.insert_one(quest)
        return result.inserted_id

    def get_available_quests(self, limit=10):
        """Get available quest templates"""
        return list(self.collection.find({"is_active": True}).limit(limit))

    def assign_quest_to_user(self, user_id, quest_id):
        """Assign a quest to a user"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        if isinstance(quest_id, str):
            quest_id = ObjectId(quest_id)

        quest = self.collection.find_one({"_id": quest_id})
        if not quest:
            return None

        user_quest = {
            "user_id": user_id,
            "quest_id": quest_id,
            "status": "accepted",  # available, accepted, in_progress, completed, failed, expired
            "accepted_at": datetime.utcnow(),
            "completed_at": None,
            "expires_at": datetime.utcnow() + timedelta(hours=quest["duration_hours"]),
            "progress": {},
            "created_at": datetime.utcnow()
        }
        result = self.user_quests.insert_one(user_quest)
        return result.inserted_id

    def get_user_quests(self, user_id, status=None):
        """Get quests for a user"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        query = {"user_id": user_id}
        if status:
            query["status"] = status

        user_quests_list = list(self.user_quests.find(query))

        # Populate quest details
        for uq in user_quests_list:
            quest_details = self.collection.find_one({"_id": uq["quest_id"]})
            uq["quest_details"] = quest_details

        return user_quests_list

    def complete_quest(self, user_quest_id):
        """Mark quest as completed"""
        if isinstance(user_quest_id, str):
            user_quest_id = ObjectId(user_quest_id)

        return self.user_quests.update_one(
            {"_id": user_quest_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": datetime.utcnow()
                }
            }
        )

    def check_expired_quests(self, user_id):
        """Check and mark expired quests"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        return self.user_quests.update_many(
            {
                "user_id": user_id,
                "status": {"$in": ["accepted", "in_progress"]},
                "expires_at": {"$lt": datetime.utcnow()}
            },
            {
                "$set": {"status": "expired"}
            }
        )
