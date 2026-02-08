"""
Experience Points & Currency Framework
Manages two-currency system: POINTS (leaderboard) and COINS (spendable)
Persists user scores to MongoDB. Stays in sync with users collection (game_points, game_currency).
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

from config.database import db_instance
from bson import ObjectId


# Two Currency System
# POINTS: Non-spendable, for leaderboard ranking
# COINS: Spendable currency for decorations/items

REWARD_VALUES = {
    # DAILY ACTIONS
    "daily_target_met": {"points": 10, "coins": 5},
    "daily_login": {"points": 5, "coins": 2},
    "extra_savings": {"points": 5, "coins": 2},  # Per $10 extra
    
    # LEVEL PROGRESSION
    "level_up": {"points": 50, "coins": 25},
    "milestone_level": {"points": 150, "coins": 75},  # Levels 10, 20, 30, 40, 50
    
    # STREAKS
    "streak_3": {"points": 30, "coins": 15},
    "streak_7": {"points": 100, "coins": 50},
    "streak_14": {"points": 200, "coins": 100},
    "streak_21": {"points": 300, "coins": 150},
    "streak_30": {"points": 500, "coins": 250},
    
    # SIDE QUESTS - NO-SPEND CHALLENGES
    "no_spend_2x": {"points": 20, "coins": 15},
    "zero_spend_day": {"points": 50, "coins": 30},
    "skip_coffee_week": {"points": 40, "coins": 25},
    "cook_5_days": {"points": 60, "coins": 35},
    
    # SIDE QUESTS - SAVINGS ACCELERATORS
    "extra_20_week": {"points": 60, "coins": 30},
    "auto_transfer": {"points": 50, "coins": 25},
    "cancel_subscription": {"points": 80, "coins": 40},
    "sell_unused": {"points": 100, "coins": 50},
    
    # SIDE QUESTS - MILESTONES
    "pay_taxes": {"points": 100, "coins": 50},
    "review_budget": {"points": 30, "coins": 15},
    "pay_off_credit": {"points": 200, "coins": 100},
    
    # SIDE QUESTS - SOCIAL
    "help_budget": {"points": 40, "coins": 20},
    "share_tip": {"points": 20, "coins": 10},
    "group_challenge": {"points": 80, "coins": 40},
}


@dataclass
class ExperienceEntry:
    """Represents a single experience point/currency entry"""
    user_id: str
    activity_type: str
    points: int
    coins: int
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""
    metadata: Dict = field(default_factory=dict)  # Extra info (streak count, level, etc)
    
    def to_dict(self) -> Dict:
        """Convert entry to dictionary format"""
        return {
            "user_id": self.user_id,
            "activity_type": self.activity_type,
            "points": self.points,
            "coins": self.coins,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "metadata": self.metadata
        }


class Scoreboard:
    """
    Two-Currency Scoreboard System
    Manages POINTS (leaderboard ranking) and COINS (spendable currency)
    Persists user scores to MongoDB
    """
    
    def __init__(self):
        """Initialize the scoreboard"""
        self.user_points: Dict[str, int] = {}  # user_id -> total_points
        self.user_coins: Dict[str, int] = {}  # user_id -> total_coins
        self.user_streaks: Dict[str, int] = {}  # user_id -> current_streak
        self.user_last_activity: Dict[str, datetime] = {}  # user_id -> last_activity_date
        self.user_names: Dict[str, str] = {}  # user_id -> username
        self.reward_history: List[ExperienceEntry] = []  # history of all rewards
        self.user_reward_breakdown: Dict[str, Dict[str, Tuple[int, int]]] = {}  # user_id -> {activity_type -> (points, coins)}
    
    def _save_to_db(self, user_id: str, username: str) -> None:
        """
        Save user's current score to MongoDB (game_scores and users collection for app sync).
        """
        try:
            db = db_instance.db
            if db is None:
                print(f"Warning: Database not connected. Score not saved for {username}")
                return

            points = self.user_points.get(user_id, 0)
            coins = self.user_coins.get(user_id, 0)
            streak = self.user_streaks.get(user_id, 0)

            # game_scores (pts history / backup)
            scores_collection = db['game_scores']
            scores_collection.update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        'user_id': user_id,
                        'username': username,
                        'points': points,
                        'coins': coins,
                        'streak': streak,
                        'updated_at': datetime.now()
                    }
                },
                upsert=True
            )

            # users collection (so app /api/me and frontend see same game_points / game_currency)
            try:
                uid = ObjectId(user_id) if isinstance(user_id, str) and len(user_id) == 24 else user_id
                db['users'].update_one(
                    {'_id': uid},
                    {
                        '$set': {
                            'game_points': points,
                            'game_currency': coins,
                            'current_streak': streak,
                            'updated_at': datetime.now()
                        }
                    }
                )
            except Exception:
                pass  # user_id may not be a valid ObjectId if pts used elsewhere
        except Exception as e:
            print(f"Error saving score to database: {e}")
    
    def _load_from_db(self, user_id: str) -> None:
        """
        Load user's score from MongoDB (game_scores first, else users collection).
        """
        try:
            db = db_instance.db
            if db is None:
                return

            # Try game_scores first
            user_score = db['game_scores'].find_one({'user_id': user_id})
            if user_score:
                self.user_points[user_id] = user_score.get('points', 0)
                self.user_coins[user_id] = user_score.get('coins', 0)
                self.user_streaks[user_id] = user_score.get('streak', 0)
                self.user_names[user_id] = user_score.get('username', user_id)
                return

            # Fallback: users collection (match rest of app)
            try:
                uid = ObjectId(user_id) if isinstance(user_id, str) and len(user_id) == 24 else user_id
                user_doc = db['users'].find_one({'_id': uid})
                if user_doc:
                    self.user_points[user_id] = user_doc.get('game_points', 0)
                    self.user_coins[user_id] = user_doc.get('game_currency', 0)
                    self.user_streaks[user_id] = user_doc.get('current_streak', 0)
                    self.user_names[user_id] = user_doc.get('username', user_doc.get('name', user_id))
            except Exception:
                pass
        except Exception as e:
            print(f"Error loading score from database: {e}")
    
    def award_reward(
        self,
        user_id: str,
        activity_type: str,
        username: str = "",
        points: Optional[int] = None,
        coins: Optional[int] = None,
        description: str = "",
        metadata: Optional[Dict] = None
    ) -> Tuple[int, int]:
        #award points and coins to a user
        
        # Initialize user if new
        if user_id not in self.user_points:
            self.user_points[user_id] = 0
            self.user_coins[user_id] = 0
            self.user_streaks[user_id] = 0
            self.user_reward_breakdown[user_id] = {}
            if username:
                self.user_names[user_id] = username
        
        # Determine reward values
        if points is None or coins is None:
            if activity_type not in REWARD_VALUES:
                raise ValueError(f"Unknown activity type: {activity_type}")
            reward = REWARD_VALUES[activity_type]
            if points is None:
                points = reward["points"]
            if coins is None:
                coins = reward["coins"]
        
        # Award to user
        self.user_points[user_id] += points
        self.user_coins[user_id] += coins
        
        # Track by activity type
        if activity_type not in self.user_reward_breakdown[user_id]:
            self.user_reward_breakdown[user_id][activity_type] = (0, 0)
        
        current_pts, current_coins = self.user_reward_breakdown[user_id][activity_type]
        self.user_reward_breakdown[user_id][activity_type] = (
            current_pts + points,
            current_coins + coins
        )
        
        # Create history entry
        entry = ExperienceEntry(
            user_id=user_id,
            activity_type=activity_type,
            points=points,
            coins=coins,
            description=description,
            metadata=metadata or {}
        )
        self.reward_history.append(entry)
        
        # Save to MongoDB
        username = username or self.user_names.get(user_id, user_id)
        self._save_to_db(user_id, username)
        
        return (points, coins)
    
    def spend_coins(self, user_id: str, amount: int, description: str = "") -> bool:
        #spend coins from a balance
        if user_id not in self.user_coins or self.user_coins[user_id] < amount:
            return False
        
        self.user_coins[user_id] -= amount
        
        # Record in history as negative
        entry = ExperienceEntry(
            user_id=user_id,
            activity_type="coins_spent",
            points=0,
            coins=-amount,
            description=description
        )
        self.reward_history.append(entry)
        
        # Save to MongoDB
        username = self.user_names.get(user_id, user_id)
        self._save_to_db(user_id, username)
        
        return True
    
    # ==================== DAILY ACTIONS ====================
    
    def check_daily_target(self, user_id: str, username: str, today_saved: float, daily_target: float) -> Tuple[int, int]:
        """
        Award points/coins for meeting daily savings target
        
        Args:
            user_id: The user ID
            username: The username
            today_saved: Amount saved today
            daily_target: Daily savings target
            
        Returns:
            tuple: (total_points, total_coins)
        """
        total_points = 0
        total_coins = 0
        
        if today_saved >= daily_target:
            # Base reward for meeting target
            pts, coins = self.award_reward(
                user_id,
                "daily_target_met",
                username=username,
                description=f"Met daily target of ${daily_target:.2f}"
            )
            total_points += pts
            total_coins += coins
            
            # Bonus for extra savings (every $10 extra)
            extra = today_saved - daily_target
            if extra > 0:
                bonus_points = int(extra / 10) * 5
                bonus_coins = int(extra / 10) * 2
                if bonus_points > 0:
                    self.user_points[user_id] += bonus_points
                    self.user_coins[user_id] += bonus_coins
                    total_points += bonus_points
                    total_coins += bonus_coins
                    
                    entry = ExperienceEntry(
                        user_id=user_id,
                        activity_type="extra_savings",
                        points=bonus_points,
                        coins=bonus_coins,
                        description=f"Bonus for ${extra:.2f} extra savings"
                    )
                    self.reward_history.append(entry)
                    self._save_to_db(user_id, username)
            
            # Update streak
            self.update_streak(user_id, username)
        
        return (total_points, total_coins)
    
    def award_login(self, user_id: str, username: str) -> Tuple[int, int]:
        """Award points for first login of the day"""
        return self.award_reward(
            user_id,
            "daily_login",
            username=username,
            description="First login today"
        )
    
    # ==================== LEVEL PROGRESSION ====================
    
    def check_level_up(self, user_id: str, username: str, new_level: int) -> Optional[Tuple[int, int]]:
        """
        Award points/coins for level up
        
        Args:
            user_id: The user ID
            username: The username
            new_level: The new level reached
            
        Returns:
            tuple: (points, coins) if level up occurred, else None
        """
        points_awarded = 0
        coins_awarded = 0
        
        # Base level up reward
        pts, coins = self.award_reward(
            user_id,
            "level_up",
            username=username,
            description=f"Reached level {new_level}",
            metadata={"level": new_level}
        )
        points_awarded += pts
        coins_awarded += coins
        
        # Milestone bonus (levels 10, 20, 30, 40, 50)
        if new_level % 10 == 0:
            pts, coins = self.award_reward(
                user_id,
                "milestone_level",
                username=username,
                description=f"Milestone! Reached level {new_level}",
                metadata={"level": new_level, "milestone": True}
            )
            points_awarded += pts
            coins_awarded += coins
        
        return (points_awarded, coins_awarded)
    
    # ==================== STREAKS ====================
    
    def update_streak(self, user_id: str, username: str = "") -> Optional[Dict]:
        """
        Update user's streak and award milestone rewards
        
        Args:
            user_id: The user ID
            username: The username (optional)
            
        Returns:
            dict: Milestone info if streak milestone reached, else None
        """
        today = datetime.now().date()
        
        if user_id not in self.user_last_activity:
            self.user_last_activity[user_id] = datetime.now()
            self.user_streaks[user_id] = 1
            return None
        
        last_activity = self.user_last_activity[user_id].date()
        yesterday = today - timedelta(days=1)
        
        if last_activity == today:
            # Already counted today
            return None
        elif last_activity == yesterday:
            # Continue streak
            self.user_streaks[user_id] += 1
        else:
            # Streak broken
            self.user_streaks[user_id] = 1
        
        self.user_last_activity[user_id] = datetime.now()
        current_streak = self.user_streaks[user_id]
        
        # Check for milestone rewards
        streak_milestones = {
            3: "streak_3",
            7: "streak_7",
            14: "streak_14",
            21: "streak_21",
            30: "streak_30"
        }
        
        if current_streak in streak_milestones:
            activity_type = streak_milestones[current_streak]
            username = username or self.user_names.get(user_id, user_id)
            pts, coins = self.award_reward(
                user_id,
                activity_type,
                username=username,
                description=f"{current_streak}-day streak achieved!",
                metadata={"streak": current_streak, "milestone": True}
            )
            
            return {
                "streak": current_streak,
                "points": pts,
                "coins": coins,
                "is_milestone": True
            }
        
        # Save to DB even without milestone
        if username:
            self._save_to_db(user_id, username)
        
        return None
    
    def get_user_streak(self, user_id: str) -> int:
        """Get current streak for user"""
        return self.user_streaks.get(user_id, 0)
    
    # ==================== SIDE QUESTS ====================
    
    def complete_quest(
        self,
        user_id: str,
        username: str,
        quest_id: str,
        quest_type: str,
        description: str = ""
    ) -> Tuple[int, int]:
        """
        Award points/coins for completing a side quest
        
        Args:
            user_id: The user ID
            username: The username
            quest_id: The quest ID
            quest_type: Type of quest (must match REWARD_VALUES key)
            description: Description of the quest
            
        Returns:
            tuple: (points, coins)
        """
        return self.award_reward(
            user_id,
            quest_type,
            username=username,
            description=description,
            metadata={"quest_id": quest_id}
        )
    
    # ==================== SCOREBOARD & LEADERBOARD ====================
    
    def get_user_points(self, user_id: str) -> int:
        """Get total points for a user"""
        return self.user_points.get(user_id, 0)
    
    def get_user_coins(self, user_id: str) -> int:
        """Get total coins for a user"""
        return self.user_coins.get(user_id, 0)
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get complete stats for a user"""
        return {
            "user_id": user_id,
            "points": self.get_user_points(user_id),
            "coins": self.get_user_coins(user_id),
            "streak": self.get_user_streak(user_id),
            "breakdown": self.user_reward_breakdown.get(user_id, {})
        }
    
    def get_leaderboard(self, limit: Optional[int] = None) -> List[Tuple]:
        """
        Get leaderboard sorted by points
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of (user_id, points) tuples sorted by points descending
        """
        sorted_scores = sorted(
            self.user_points.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        if limit:
            sorted_scores = sorted_scores[:limit]
        
        return sorted_scores
    
    def get_user_rank(self, user_id: str) -> Optional[int]:
        """Get the rank (position) of a user on the leaderboard (1-indexed)"""
        leaderboard = self.get_leaderboard()
        for rank, (uid, _) in enumerate(leaderboard, start=1):
            if uid == user_id:
                return rank
        return None
    
    def get_user_history(self, user_id: str, limit: Optional[int] = None) -> List[ExperienceEntry]:
        """Get all reward entries for a specific user"""
        user_history = [entry for entry in self.reward_history if entry.user_id == user_id]
        if limit:
            user_history = user_history[-limit:]
        return user_history
    
    def get_recent_activity(self, limit: int = 10) -> List[ExperienceEntry]:
        """Get most recent reward entries across all users"""
        return self.reward_history[-limit:]
    
    def reset_user(self, user_id: str) -> None:
        """Reset a user's points, coins, and streak"""
        if user_id in self.user_points:
            self.user_points[user_id] = 0
            self.user_coins[user_id] = 0
            self.user_streaks[user_id] = 0
            self.user_reward_breakdown[user_id] = {}
            self.reward_history = [
                entry for entry in self.reward_history
                if entry.user_id != user_id
            ]
    
    def export_scoreboard(self) -> Dict:
        """Export entire scoreboard data"""
        return {
            "user_points": self.user_points,
            "user_coins": self.user_coins,
            "user_streaks": self.user_streaks,
            "leaderboard": self.get_leaderboard(),
            "user_breakdown": self.user_reward_breakdown,
            "total_entries": len(self.reward_history)
        }


# Global scoreboard instance
scoreboard = Scoreboard()


if __name__ == "__main__":
    # Run from backend: python pts.py
    import os
    if os.path.dirname(__file__):
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv()
    db = db_instance.connect()
    print("pts: database connected. Scoreboard ready.")
    print("  Use: from pts import scoreboard; scoreboard.award_reward(user_id, 'daily_login', username='...')")

