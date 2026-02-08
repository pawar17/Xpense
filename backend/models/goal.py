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

        # New goals go at end of queue
        last = self.collection.find_one({"user_id": user_id}, sort=[("order", -1)], projection={"order": 1})
        next_order = (last["order"] + 1) if last and "order" in last else 0
        # If user already has an active goal, new goal starts as queued
        has_active = self.collection.find_one({"user_id": user_id, "status": "active"})
        initial_status = "queued" if has_active else "active"

        goal = {
            "user_id": user_id,
            "goal_name": goal_name,
            "goal_category": goal_category,  # house, vacation, debt, shopping, emergency, other
            "target_amount": target_amount,
            "current_amount": 0,
            "target_date": target_date,
            "total_levels": 10,
            "current_level": 0,
            "daily_target": 0,
            "level_thresholds": [],
            "status": initial_status,  # active, completed, paused, queued
            "order": next_order,  # queue order: lower = higher priority
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

        return list(self.collection.find(query).sort([("order", 1), ("created_at", -1)]))

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

    def _activate_next_goal(self, user_id, after_order):
        """Set the next goal (by order) to active when current goal is completed."""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        next_goal = self.collection.find_one(
            {"user_id": user_id, "order": {"$gt": after_order}, "status": {"$in": ["queued", "paused"]}},
            sort=[("order", 1)]
        )
        if next_goal:
            self.collection.update_one(
                {"_id": next_goal["_id"]},
                {"$set": {"status": "active", "updated_at": datetime.utcnow()}}
            )
        return next_goal

    def contribute(self, goal_id, amount):
        """Add money to a goal. Caps at target; returns (result, remainder)."""
        if isinstance(goal_id, str):
            goal_id = ObjectId(goal_id)

        goal = self.get_goal_by_id(goal_id)
        if not goal:
            return None, amount

        target = goal["target_amount"]
        current = goal["current_amount"]
        # Cap at target so we don't overfill; remainder goes to next goal
        amount_to_add = min(amount, max(0, target - current))
        remainder = amount - amount_to_add
        new_amount = current + amount_to_add

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
        if new_amount >= target:
            status = "completed"
            completed_at = datetime.utcnow()

        result = self.collection.update_one(
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
        if status == "completed":
            self._activate_next_goal(goal["user_id"], goal["order"])
        return result, remainder

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

    def get_manifestation_goal(self, user_id):
        """Get the #1 priority goal (lowest order number) for display on dashboard"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        # Get active or queued goal with lowest order (highest priority)
        return self.collection.find_one(
            {"user_id": user_id, "status": {"$in": ["active", "queued"]}},
            sort=[("order", 1)]  # Ascending order = lowest first
        )

    def check_expired_goals(self, user_id):
        """Check for goals past their target_date with no contributions and mark as pending"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        now = datetime.utcnow()

        # Find goals that are past deadline with $0 saved
        expired_goals = self.collection.find({
            "user_id": user_id,
            "status": {"$in": ["active", "queued"]},
            "target_date": {"$lt": now},
            "current_amount": 0
        })

        updated_count = 0
        for goal in expired_goals:
            self.collection.update_one(
                {"_id": goal["_id"]},
                {
                    "$set": {
                        "status": "pending",
                        "updated_at": now
                    }
                }
            )
            updated_count += 1

        return updated_count

    def archive_goal(self, goal_id, user_id):
        """Move a completed or pending goal to archive"""
        if isinstance(goal_id, str):
            goal_id = ObjectId(goal_id)
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        goal = self.get_goal_by_id(goal_id)
        if not goal or goal["user_id"] != user_id:
            return None

        # Only archive completed or pending goals
        if goal["status"] not in ["completed", "pending"]:
            return None

        result = self.collection.update_one(
            {"_id": goal_id, "user_id": user_id},
            {
                "$set": {
                    "status": "archived",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result

    def get_archived_goals(self, user_id):
        """Get all archived goals for a user"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        return list(self.collection.find(
            {"user_id": user_id, "status": "archived"}
        ).sort("completed_at", -1))

    def delete_goal(self, goal_id, user_id):
        """Delete a goal (only if archived)"""
        if isinstance(goal_id, str):
            goal_id = ObjectId(goal_id)
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        # Only allow deleting archived goals
        result = self.collection.delete_one({
            "_id": goal_id,
            "user_id": user_id,
            "status": "archived"
        })
        return result.deleted_count > 0
