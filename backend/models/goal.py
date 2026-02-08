from datetime import datetime
from bson import ObjectId

class Goal:
    def __init__(self, db):
        self.collection = db.goals
        self._create_indexes()

    def _create_indexes(self):
        """Create indexes for better query performance"""
        self.collection.create_index("user_id")
        self.collection.create_index([("user_id", 1), ("status", 1)])

    def create_goal(self, user_id, goal_name, goal_category, target_amount, target_date=None):
        """Create a new savings goal"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        goal = {
            "user_id": user_id,
            "goal_name": goal_name,
            "goal_category": goal_category,  # house, vacation, debt, shopping, emergency, other
            "target_amount": target_amount,
            "current_amount": 0,
            "target_date": target_date,
            "total_levels": 10,  # Default, will be updated by AI
            "current_level": 0,
            "daily_target": 0,
            "level_thresholds": [],
            "status": "active",  # active, completed, paused
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None
        }
        result = self.collection.insert_one(goal)
        return result.inserted_id

    def get_user_goals(self, user_id, status=None):
        """Get all goals for a user"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        query = {"user_id": user_id}
        if status:
            query["status"] = status

        return list(self.collection.find(query).sort("created_at", -1))

    def get_goal_by_id(self, goal_id):
        """Get a specific goal"""
        if isinstance(goal_id, str):
            goal_id = ObjectId(goal_id)
        return self.collection.find_one({"_id": goal_id})

    def update_goal(self, goal_id, update_data):
        """Update goal data"""
        if isinstance(goal_id, str):
            goal_id = ObjectId(goal_id)
        update_data["updated_at"] = datetime.utcnow()
        return self.collection.update_one(
            {"_id": goal_id},
            {"$set": update_data}
        )

    def contribute(self, goal_id, amount):
        """Add money to a goal"""
        if isinstance(goal_id, str):
            goal_id = ObjectId(goal_id)

        goal = self.get_goal_by_id(goal_id)
        if not goal:
            return None

        new_amount = goal["current_amount"] + amount

        # Calculate new level
        new_level = goal["current_level"]
        if goal["level_thresholds"]:
            for i, threshold in enumerate(goal["level_thresholds"]):
                if new_amount >= threshold:
                    new_level = i + 1
                else:
                    break

        # Check if goal is completed
        status = goal["status"]
        completed_at = goal.get("completed_at")
        if new_amount >= goal["target_amount"]:
            status = "completed"
            completed_at = datetime.utcnow()

        return self.collection.update_one(
            {"_id": goal_id},
            {
                "$set": {
                    "current_amount": new_amount,
                    "current_level": new_level,
                    "status": status,
                    "completed_at": completed_at,
                    "updated_at": datetime.utcnow()
                }
            }
        )

    def set_level_system(self, goal_id, total_levels, level_thresholds, daily_target):
        """Update goal with AI-calculated level system"""
        if isinstance(goal_id, str):
            goal_id = ObjectId(goal_id)

        return self.collection.update_one(
            {"_id": goal_id},
            {
                "$set": {
                    "total_levels": total_levels,
                    "level_thresholds": level_thresholds,
                    "daily_target": daily_target,
                    "updated_at": datetime.utcnow()
                }
            }
        )
