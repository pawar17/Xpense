from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import config and models
from config.database import db_instance
from models.user import User
from models.goal import Goal
from models.side_quest import SideQuest
from models.daily_flow import DailyFlow
from models.veto_request import VetoRequest as VetoRequestModel
from utils.auth import hash_password, verify_password, check_user_password, create_access_token, jwt_required
from utils.nessie import (
    get_customer_accounts, get_all_transactions, get_account,
    get_all_customers
)
from utils.ai_calculator import calculate_levels_with_ai, ai_chat_assistant
from utils.statement_parser import (
    parse_and_extract_transactions,
    categorize_transactions_with_ai,
)
from data.mock_statement_v4 import (
    get_mock_spending_analysis,
    get_mock_suggestion,
    get_mock_quests_from_spending,
)
from models.bank_statement import BankStatement
from models.nudge import Nudge
from models.post import Post
from werkzeug.utils import secure_filename
import uuid

# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Connect to database
db = db_instance.connect()

# Initialize models
user_model = User(db)
goal_model = Goal(db)
quest_model = SideQuest(db)
daily_flow_model = DailyFlow(db)
veto_request_model = VetoRequestModel(db)
bank_statement_model = BankStatement(db)
nudge_model = Nudge(db)
post_model = Post(db)


def _serialize_user_for_json(user):
    """Return a JSON-serializable copy of user (ObjectId -> str, datetime -> iso)."""
    if not user:
        return None
    from bson import ObjectId
    from datetime import datetime
    out = {}
    for k, v in user.items():
        if k == "password_hash":
            continue
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat() + "Z" if v.tzinfo is None else v.isoformat()
        elif isinstance(v, list) and v and isinstance(v[0], ObjectId):
            out[k] = [str(x) for x in v]
        else:
            out[k] = v
    return out


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.json
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        country = data.get('country', 'USA')
        state = data.get('state', '')

        # Validation
        if not all([username, email, password, name]):
            return jsonify({"error": "Missing required fields"}), 400

        # Check if user exists
        if user_model.find_by_username(username):
            return jsonify({"error": "Username already exists"}), 400

        if user_model.find_by_email(email):
            return jsonify({"error": "Email already exists"}), 400

        # Hash password and create user
        password_hash = hash_password(password)
        user_id = user_model.create_user(
            username=username,
            email=email,
            password_hash=password_hash,
            name=name,
            country=country,
            state=state
        )

        # Create JWT token
        token = create_access_token({"user_id": str(user_id)})

        return jsonify({
            "message": "User registered successfully",
            "token": token,
            "user_id": str(user_id)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json(silent=True) or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''

        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400

        # Find user (case-insensitive)
        user = user_model.find_by_username(username.lower())
        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        # Verify password (supports password_hash or plain password field)
        if not check_user_password(password, user):
            return jsonify({"error": "Invalid credentials"}), 401

        # Create JWT token
        token = create_access_token({"user_id": str(user['_id'])})

        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "id": str(user['_id']),
                "username": user.get('username', ''),
                "name": user.get('name') or user.get('username', ''),
                "email": user.get('email', '')
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# USER ROUTES
# ============================================================================

@app.route('/api/users/profile', methods=['GET'])
@jwt_required
def get_profile():
    """Get current user profile"""
    try:
        user = user_model.find_by_id(request.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"user": _serialize_user_for_json(user)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/profile', methods=['PATCH'])
@jwt_required
def update_profile():
    """Update current user profile (name only for safety)"""
    try:
        data = request.json or {}
        name = data.get('name')

        if name is not None:
            if not isinstance(name, str) or len(name.strip()) == 0:
                return jsonify({"error": "Name must be a non-empty string"}), 400
            user_model.update_user(request.user_id, {"name": name.strip()})

        user = user_model.find_by_id(request.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"user": _serialize_user_for_json(user)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/gamification/stats', methods=['GET'])
@jwt_required
def get_game_stats():
    """Get user's game statistics. Streak is computed from daily_flow when available."""
    try:
        user = user_model.find_by_id(request.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Streak from streak calculator (daily_flow); fallback to stored current_streak
        try:
            streak = daily_flow_model.calculate_streak(request.user_id)
        except Exception:
            streak = user.get('current_streak', 0)

        # Rank by XP: 1 + number of users with strictly more game_points
        my_points = user.get('game_points', 0)
        above = user_model.collection.count_documents({"game_points": {"$gt": my_points}})
        rank = above + 1

        placements = user.get('pop_city_placements')
        if not isinstance(placements, dict):
            placements = {}
        placements = dict(placements)
        placement_count = len(placements)
        # Every 4 items = 1 vote you can ask for (request a veto)
        veto_earned = placement_count // 4
        veto_tokens = veto_earned
        # One full row in the grid = 1 "Go for it" you can give; two full rows = 2, etc.
        approve_earned = _count_full_rows(placements)
        approve_used = veto_request_model.count_approvals_by_user(request.user_id)
        approve_tokens = max(0, approve_earned - approve_used)

        return jsonify({
            "points": user.get('game_points', 0),
            "currency": user.get('game_currency', 0),
            "streak": streak,
            "longest_streak": user.get('longest_streak', 0),
            "rank": rank,
            "pop_city_placements": placements,
            "veto_tokens": veto_tokens,
            "veto_earned": veto_earned,
            "veto_used": 0,
            "pop_city_placement_count": placement_count,
            "approve_tokens": approve_tokens,
            "approve_earned": approve_earned,
            "approve_used": approve_used,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


POP_CITY_COST = 25
POP_CITY_POINTS = 25
POP_CITY_ROWS = 5
POP_CITY_COLS = 5


def _count_full_rows(placements, rows=POP_CITY_ROWS, cols=POP_CITY_COLS):
    """Number of complete rows in the 5x5 grid. One full row = 1 vote on someone else's veto."""
    if not isinstance(placements, dict):
        placements = {}
    # Normalize keys to str so we count correctly whether DB has "0" or 0
    keys = {str(k) for k in placements}
    full = 0
    for r in range(rows):
        if all(str(r * cols + c) in keys for c in range(cols)):
            full += 1
    return full


@app.route('/api/gamification/pop-city-place', methods=['POST'])
@jwt_required
def pop_city_place():
    """Spend 25 currency, add 25 XP, and save the placement in Pop City. Body: { index: number, item: string }."""
    try:
        user = user_model.find_by_id(request.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        current_currency = user.get('game_currency', 0)
        if current_currency < POP_CITY_COST:
            return jsonify({"error": "Not enough coins", "currency": current_currency}), 400
        data = request.get_json(silent=True) or {}
        index = data.get('index')
        item = data.get('item')
        if index is None or not isinstance(index, (int, float)) or index < 0 or index >= 25:
            return jsonify({"error": "Invalid index"}), 400
        index = int(index)
        if not item or not isinstance(item, str):
            return jsonify({"error": "Invalid item"}), 400
        placements = dict(user.get('pop_city_placements') or {})
        placements[str(index)] = item
        user_model.update_user(request.user_id, {"pop_city_placements": placements})
        user_model.update_game_stats(request.user_id, points=POP_CITY_POINTS, currency=-POP_CITY_COST)
        user = user_model.find_by_id(request.user_id)
        try:
            streak = daily_flow_model.calculate_streak(request.user_id)
        except Exception:
            streak = user.get('current_streak', 0)
        placements_after = user.get('pop_city_placements')
        if not isinstance(placements_after, dict):
            placements_after = {}
        placements_after = dict(placements_after)
        placement_count = len(placements_after)
        veto_earned = placement_count // 4
        veto_tokens = veto_earned
        approve_earned = _count_full_rows(placements_after)
        approve_used = veto_request_model.count_approvals_by_user(request.user_id)
        approve_tokens = max(0, approve_earned - approve_used)
        return jsonify({
            "points_earned": POP_CITY_POINTS,
            "currency_spent": POP_CITY_COST,
            "placements": placements_after,
            "veto_tokens": veto_tokens,
            "stats": {
                "points": user.get('game_points', 0),
                "currency": user.get('game_currency', 0),
                "streak": streak,
                "longest_streak": user.get('longest_streak', 0),
                "veto_tokens": veto_tokens,
                "veto_earned": veto_earned,
                "veto_used": 0,
                "pop_city_placement_count": placement_count,
                "approve_tokens": approve_tokens,
                "approve_earned": approve_earned,
                "approve_used": approve_used,
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/gamification/streak-calendar', methods=['GET'])
@jwt_required
def get_streak_calendar():
    """Get which days in a month had positive net (achieved). Query: year, month (default: current)."""
    try:
        from datetime import datetime as dt
        from calendar import monthrange
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        now = dt.utcnow()
        if not year:
            year = now.year
        if not month:
            month = now.month
        start = dt(year, month, 1)
        last_day = monthrange(year, month)[1]
        end = dt(year, month, last_day)
        entries = daily_flow_model.get_user_entries(request.user_id, start_date=start, end_date=end)
        days_achieved = []
        for e in entries:
            net = e.get("net")
            if net is None:
                inc = float(e.get("income") or 0)
                exp = float(e.get("expenses") if e.get("expenses") is not None else e.get("expense") or 0)
                net = inc - exp
            if net >= 0 and e.get("date"):
                d = e["date"]
                if hasattr(d, "day"):
                    days_achieved.append(d.day)
                else:
                    days_achieved.append(int(str(d)[8:10]))
        return jsonify({"year": year, "month": month, "days": sorted(set(days_achieved))}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/gamification/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard rankings by XP (game_points)."""
    try:
        limit = int(request.args.get('limit', 100))
        leaderboard = user_model.get_leaderboard(limit=limit)
        rankings = []
        for i, user in enumerate(leaderboard):
            rankings.append({
                "rank": i + 1,
                "user_id": str(user['_id']),
                "username": user.get('username', ''),
                "name": user.get('name', ''),
                "points": user.get('game_points', 0),
                "streak": user.get('current_streak', 0)
            })
        return jsonify({"leaderboard": rankings}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/gamification/leaderboard/friends', methods=['GET'])
@jwt_required
def get_friends_leaderboard():
    """Get current user + friends ranked by XP."""
    try:
        from bson import ObjectId
        user = user_model.find_by_id(request.user_id)
        if not user:
            return jsonify({"leaderboard": []}), 200
        friend_ids = list(user.get("friends") or [])
        current_oid = ObjectId(request.user_id) if isinstance(request.user_id, str) else request.user_id
        ids_to_fetch = [current_oid] + [
            fid if isinstance(fid, ObjectId) else ObjectId(fid) for fid in friend_ids
        ]
        users = list(user_model.collection.find(
            {"_id": {"$in": ids_to_fetch}},
            {"username": 1, "name": 1, "game_points": 1, "current_streak": 1}
        ))
        users.sort(key=lambda u: u.get('game_points', 0), reverse=True)
        rankings = []
        for i, u in enumerate(users):
            rankings.append({
                "rank": i + 1,
                "user_id": str(u['_id']),
                "username": u.get('username', ''),
                "name": u.get('name', ''),
                "points": u.get('game_points', 0),
                "streak": u.get('current_streak', 0)
            })
        return jsonify({"leaderboard": rankings}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# GOAL ROUTES
# ============================================================================

@app.route('/api/goals', methods=['POST'])
@jwt_required
def create_goal():
    """Create a new savings goal"""
    try:
        data = request.json
        goal_name = data.get('goal_name')
        goal_category = data.get('goal_category', 'other')
        target_amount = data.get('target_amount')
        target_date = data.get('target_date')

        if not goal_name or not target_amount:
            return jsonify({"error": "Missing required fields"}), 400

        # Create goal
        goal_id = goal_model.create_goal(
            user_id=request.user_id,
            goal_name=goal_name,
            goal_category=goal_category,
            target_amount=float(target_amount),
            target_date=target_date
        )

        # Calculate levels with AI (use bank statement income/expenses when available)
        goal = goal_model.get_goal_by_id(goal_id)
        user = user_model.find_by_id(request.user_id)
        monthly_income = 3000
        avg_expenses = 2200
        try:
            txns = bank_statement_model.get_user_transactions(request.user_id, limit=500)
            if txns:
                income = sum(float(t.get('amount') or 0) for t in txns if float(t.get('amount') or 0) > 0)
                expenses = sum(abs(float(t.get('amount') or 0)) for t in txns if float(t.get('amount') or 0) < 0)
                if income > 0 or expenses > 0:
                    monthly_income = max(1, round(income, 2)) if income > 0 else 3000
                    avg_expenses = round(expenses, 2) if expenses > 0 else 2200
        except Exception:
            pass

        ai_result = calculate_levels_with_ai(
            {
                'target_amount': float(target_amount),
                'current_amount': 0,
                'category': goal_category,
                'target_date': target_date
            },
            {
                'monthly_income': monthly_income,
                'avg_expenses': avg_expenses,
                'current_streak': user.get('current_streak', 0),
                'from_bank_statement': monthly_income != 3000 or avg_expenses != 2200,
            }
        )

        # Update goal with AI calculations
        goal_model.set_level_system(
            goal_id,
            ai_result['total_levels'],
            ai_result['level_thresholds'],
            ai_result['daily_target']
        )

        goal = goal_model.get_goal_by_id(goal_id)
        goal['_id'] = str(goal['_id'])
        goal['user_id'] = str(goal['user_id'])
        goal['ai_suggestions'] = ai_result.get('ai_suggestions', {})

        return jsonify({
            "message": "Goal created successfully",
            "goal": goal
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/goals', methods=['GET'])
@jwt_required
def get_goals():
    """Get all user goals (active, queued, pending, completed). Archived goals are excluded; use GET /goals/archived."""
    try:
        goals = goal_model.get_user_goals(request.user_id, exclude_archived=True)
        return jsonify({"goals": [_format_goal(g) for g in goals]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/goals/<goal_id>/contribute', methods=['POST'])
@jwt_required
def contribute_to_goal(goal_id):
    """Add money to a goal"""
    try:
        data = request.json
        amount = data.get('amount')

        if not amount or float(amount) <= 0:
            return jsonify({"error": "Invalid amount"}), 400

        goal = goal_model.get_goal_by_id(goal_id)
        if not goal:
            return jsonify({"error": "Goal not found"}), 404

        if str(goal['user_id']) != request.user_id:
            return jsonify({"error": "Unauthorized"}), 403

        # Get old level
        old_level = goal['current_level']
        amount_left = float(amount)

        # Contribute (caps at target; remainder can go to next goal)
        result, remainder = goal_model.contribute(goal_id, amount_left)
        if result is None:
            return jsonify({"error": "Goal not found"}), 404
        amount_left = remainder
        # If contribution exceeded goal target, apply remainder to next active goal
        while amount_left > 0:
            goals = goal_model.get_user_goals(request.user_id, exclude_archived=True)
            next_active = next((g for g in goals if g["status"] == "active"), None)
            if not next_active:
                break
            next_id = str(next_active["_id"])
            if next_id == str(goal_id):
                break
            result, remainder = goal_model.contribute(next_id, amount_left)
            if result is None:
                break
            amount_left = remainder

        # Get updated goal (the one user originally contributed to; may be archived now)
        updated_goal = goal_model.get_goal_by_id(goal_id)
        new_level = updated_goal['current_level'] if updated_goal else old_level
        is_completed = updated_goal and updated_goal['status'] in ('completed', 'archived')
        was_not_completed = goal['status'] not in ('completed', 'archived')

        # Award points if leveled up
        points_earned = 0
        currency_earned = 0

        if new_level > old_level:
            points_earned = (new_level - old_level) * 50
            currency_earned = (new_level - old_level) * 25

        # Bonus when goal is just achieved: +10 XP base, +5 XP if completed on or before target date
        if is_completed and was_not_completed:
            points_earned += 10
            on_time = False
            if updated_goal.get('target_date') and updated_goal.get('completed_at'):
                from datetime import datetime
                td = updated_goal['target_date']
                ca = updated_goal['completed_at']
                if isinstance(td, str):
                    td = datetime.fromisoformat(td.replace('Z', '+00:00'))
                try:
                    t_naive = td.replace(tzinfo=None) if getattr(td, 'tzinfo', None) else td
                    c_naive = ca.replace(tzinfo=None) if getattr(ca, 'tzinfo', None) else ca
                    on_time = c_naive <= t_naive
                except Exception:
                    on_time = True
            if on_time and updated_goal.get('target_date'):
                points_earned += 5
                message = "🎉 Goal achieved on time! +15 XP bonus!"
            else:
                message = "🎉 Goal completed! +10 XP bonus!"
        elif new_level > old_level:
            message = "Level up!"
        else:
            message = "Contribution added"

        if points_earned > 0 or currency_earned > 0:
            user_model.update_game_stats(request.user_id, points=points_earned, currency=currency_earned)

        return jsonify({
            "message": message,
            "goal": _format_goal(updated_goal),
            "level_up": new_level > old_level,
            "goal_completed": is_completed and was_not_completed,
            "new_level": new_level,
            "rewards": {
                "points": points_earned,
                "currency": currency_earned
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# SIDE QUEST ROUTES
# ============================================================================

@app.route('/api/quests/available', methods=['GET'])
@jwt_required
def get_available_quests():
    """Get available quests (excludes ones user has already accepted or completed)."""
    try:
        quests = quest_model.get_available_quests(limit=10, user_id=request.user_id)

        # Format response
        for quest in quests:
            quest['_id'] = str(quest['_id'])

        return jsonify({"quests": quests}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/quests/<quest_id>/accept', methods=['POST'])
@jwt_required
def accept_quest(quest_id):
    """Accept a quest"""
    try:
        user_quest_id = quest_model.assign_quest_to_user(request.user_id, quest_id)

        if not user_quest_id:
            return jsonify({"error": "Quest not found"}), 404

        return jsonify({
            "message": "Quest accepted",
            "user_quest_id": str(user_quest_id)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/quests/active', methods=['GET'])
@jwt_required
def get_active_quests():
    """Get user's active quests"""
    try:
        quests = quest_model.get_user_quests(request.user_id, status="accepted")

        # Format response
        for quest in quests:
            quest['_id'] = str(quest['_id'])
            quest['user_id'] = str(quest['user_id'])
            quest['quest_id'] = str(quest['quest_id'])
            if quest.get('quest_details'):
                quest['quest_details']['_id'] = str(quest['quest_details']['_id'])

        return jsonify({"quests": quests}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/quests/<user_quest_id>/complete', methods=['POST'])
@jwt_required
def complete_quest(user_quest_id):
    """Complete a quest"""
    try:
        # Get quest details
        from bson import ObjectId
        user_quest = quest_model.user_quests.find_one({"_id": ObjectId(user_quest_id)})

        if not user_quest:
            return jsonify({"error": "Quest not found"}), 404

        if str(user_quest['user_id']) != request.user_id:
            return jsonify({"error": "Unauthorized"}), 403

        # Get quest template
        quest_template = quest_model.collection.find_one({"_id": user_quest['quest_id']})

        # Mark as completed
        quest_model.complete_quest(user_quest_id)

        # Award rewards
        points = quest_template.get('points_reward', 0)
        currency = quest_template.get('currency_reward', 0)
        user_model.update_game_stats(request.user_id, points=points, currency=currency)

        return jsonify({
            "message": "Quest completed!",
            "rewards": {
                "points": points,
                "currency": currency
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# VETO REQUESTS (cross-user: Anna creates, Suhani sees)
# ============================================================================

def _format_veto_request(doc):
    if not doc:
        return None
    votes = doc.get("votes") or []
    return {
        "id": str(doc["_id"]),
        "requesterId": str(doc.get("user_id", "")),
        "user": {
            "name": doc.get("name") or doc.get("username", ""),
            "username": doc.get("username", ""),
            "avatar": (doc.get("name") or doc.get("username") or "?")[0].upper(),
        },
        "item": doc.get("item", ""),
        "amount": doc.get("amount", 0),
        "reason": doc.get("reason", ""),
        "votes": [{"userId": v.get("userId"), "vote": v.get("vote")} for v in votes],
        "status": doc.get("status", "pending"),
    }


@app.route('/api/veto-requests', methods=['GET'])
@jwt_required
def list_veto_requests():
    """Pending requests + current user's own approved/rejected (so requester sees outcome)."""
    try:
        docs = veto_request_model.get_visible_for_user(request.user_id)
        return jsonify({"vetoRequests": [_format_veto_request(d) for d in docs]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/veto-requests', methods=['POST'])
@jwt_required
def create_veto_request():
    """Create a veto request (Anna requests, stored in DB)."""
    try:
        data = request.get_json(silent=True) or {}
        item = (data.get("item") or "").strip()
        amount = data.get("amount")
        reason = (data.get("reason") or "").strip()
        if not item or reason is None:
            return jsonify({"error": "Item and reason are required"}), 400
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return jsonify({"error": "Amount must be a number"}), 400
        user = user_model.find_by_id(request.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        req_id = veto_request_model.create(
            user_id=request.user_id,
            username=user.get("username", ""),
            name=user.get("name", ""),
            item=item,
            amount=amount,
            reason=reason,
        )
        doc = veto_request_model.get_by_id(req_id)
        return jsonify({"message": "Sent to Veto Court!", "vetoRequest": _format_veto_request(doc)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/veto-requests/<request_id>/vote', methods=['POST'])
@jwt_required
def vote_veto_request(request_id):
    """Vote Go for it or Veto on a request. Requester cannot vote on their own. Go for it requires 5 items (one row) in Pop City."""
    try:
        data = request.get_json(silent=True) or {}
        vote = (data.get("vote") or "").strip().lower()
        if vote not in ("approve", "veto"):
            return jsonify({"error": "Vote must be 'approve' or 'veto'"}), 400
        doc = veto_request_model.get_by_id(request_id)
        if not doc:
            return jsonify({"error": "Veto request not found"}), 404
        if str(doc.get("user_id")) == request.user_id:
            return jsonify({"error": "You cannot vote on your own request"}), 400
        # "Go for it" only if you have at least one full row in Pop City; each full row = 1 vote on someone else's veto
        if vote == "approve":
            user = user_model.find_by_id(request.user_id)
            raw = (user or {}).get("pop_city_placements")
            placements = dict(raw) if isinstance(raw, dict) else {}
            approve_earned = _count_full_rows(placements)
            approve_used = veto_request_model.count_approvals_by_user(request.user_id)
            if approve_earned - approve_used < 1:
                return jsonify({
                    "error": "Fill one full row in Pop City (Play tab) to vote Go for it on someone else's request. Two full rows = 2 votes."
                }), 400
        doc = veto_request_model.add_vote(request_id, request.user_id, vote)
        if not doc:
            return jsonify({"error": "Veto request not found"}), 404
        rejected = doc.get("status") == "rejected"
        return jsonify({
            "message": "Rejected" if rejected else "Vote recorded",
            "rejected": rejected,
            "vetoRequest": _format_veto_request(doc),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# BANKING (NESSIE API) ROUTES
# ============================================================================

@app.route('/api/banking/customers', methods=['GET'])
def get_customers():
    """Get all Nessie customers (for demo/testing)"""
    try:
        customers = get_all_customers()
        return jsonify({"customers": customers}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/banking/accounts/<customer_id>', methods=['GET'])
def get_accounts(customer_id):
    """Get customer's bank accounts"""
    try:
        accounts = get_customer_accounts(customer_id)
        return jsonify({"accounts": accounts}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/banking/transactions/<account_id>', methods=['GET'])
def get_transactions(account_id):
    """Get account transactions"""
    try:
        transactions = get_all_transactions(account_id)
        return jsonify({"transactions": transactions}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# AI ASSISTANT ROUTES
# ============================================================================

@app.route('/api/ai/chat', methods=['POST'])
@jwt_required
def ai_chat():
    """Chat with AI assistant"""
    try:
        data = request.json
        message = data.get('message')

        if not message:
            return jsonify({"error": "Message is required"}), 400

        # Get user context
        user = user_model.find_by_id(request.user_id)
        goals = goal_model.get_user_goals(request.user_id, status="active")

        context = {
            'name': user.get('name', 'there'),
            'points': user.get('game_points', 0),
            'currency': user.get('game_currency', 0),
            'current_streak': user.get('current_streak', 0)
        }

        if goals:
            goal = goals[0]
            context.update({
                'goal_name': goal.get('goal_name'),
                'current_amount': goal.get('current_amount', 0),
                'target_amount': goal.get('target_amount', 0),
                'progress_percent': round((goal.get('current_amount', 0) / goal.get('target_amount', 1)) * 100, 1)
            })

        response = ai_chat_assistant(message, context)

        return jsonify({"response": response}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# BANK STATEMENTS (upload PDF, parse, categorize, spending analysis)
# ============================================================================

@app.route('/api/bank-statements/upload', methods=['POST'])
@jwt_required
def upload_bank_statement():
    """Upload a bank statement PDF; parse and store transactions."""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Only PDF files are allowed"}), 400

        filename = secure_filename(file.filename) or "statement.pdf"
        unique = str(uuid.uuid4())[:8]
        save_name = f"{request.user_id}_{unique}_{filename}"
        path = os.path.join(app.config['UPLOAD_FOLDER'], save_name)
        file.save(path)

        transactions = parse_and_extract_transactions(path)
        transactions = categorize_transactions_with_ai(transactions)

        statement_id = bank_statement_model.create(
            request.user_id,
            filename=filename,
            file_size_bytes=os.path.getsize(path),
        )
        bank_statement_model.insert_transactions(
            request.user_id,
            statement_id,
            [{"date": t.get("date"), "description": t.get("description", ""), "amount": t.get("amount", 0), "category": t.get("category", "other")} for t in transactions]
        )

        return jsonify({
            "message": "Statement uploaded and processed",
            "statementId": str(statement_id),
            "transactionCount": len(transactions),
        }), 201
    except ImportError as e:
        return jsonify({"error": "PDF parsing not available. Install pdfplumber."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/bank-statements', methods=['GET'])
@jwt_required
def list_bank_statements():
    """List user's uploaded statements."""
    try:
        docs = bank_statement_model.get_user_statements(request.user_id)
        out = []
        for d in docs:
            d['_id'] = str(d['_id'])
            d['user_id'] = str(d.get('user_id', ''))
            out.append(d)
        from bson import ObjectId
        uid = ObjectId(request.user_id) if isinstance(request.user_id, str) else request.user_id
        total_txs = bank_statement_model.transactions.count_documents({"user_id": uid})
        return jsonify({"statements": out, "totalTransactions": total_txs}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/bank-statements/<statement_id>', methods=['DELETE'])
@jwt_required
def delete_bank_statement(statement_id):
    """Delete a statement and all its transactions."""
    try:
        doc = bank_statement_model.get_by_id(statement_id)
        if not doc or str(doc.get("user_id")) != request.user_id:
            return jsonify({"error": "Statement not found"}), 404
        deleted = bank_statement_model.delete_statement(statement_id, request.user_id)
        return jsonify({"message": "Statement deleted", "transactionsRemoved": deleted}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/bank-statements/spending-analysis', methods=['GET'])
@jwt_required
def spending_analysis():
    """Get spending by category and suggested daily savings. Shows financial breakdown only after user has uploaded at least one PDF (then uses hardcoded v4 data so it appears the PDF was read)."""
    try:
        statements = bank_statement_model.get_user_statements(request.user_id, limit=1)
        has_uploaded_statement = len(statements) > 0

        goals = goal_model.get_user_goals(request.user_id, status="active")
        goal = goals[0] if goals else None
        target_amount = float(goal.get("target_amount", 0) or 0) if goal else 0
        current_amount = float(goal.get("current_amount", 0) or 0) if goal else 0
        target_date = goal.get("target_date") if goal else None
        goal_name = goal.get("goal_name", "") if goal else ""

        if has_uploaded_statement:
            mock = get_mock_spending_analysis()
            spending_by_category = mock["spendingByCategory"]
            transaction_count = mock["transactionCount"]
            suggestion = get_mock_suggestion(target_amount, current_amount, target_date, goal_name)
            return jsonify({
                "spendingByCategory": spending_by_category,
                "suggestion": suggestion,
                "goalName": goal_name,
                "transactionCount": transaction_count,
                "hasStatementData": True,
            }), 200
        else:
            suggestion = get_mock_suggestion(target_amount, current_amount, target_date, goal_name)
            return jsonify({
                "spendingByCategory": {},
                "suggestion": suggestion,
                "goalName": goal_name,
                "transactionCount": 0,
                "hasStatementData": False,
            }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# GOALS: PATCH (edit), REORDER (queue)
# ============================================================================

@app.route('/api/goals/<goal_id>', methods=['PATCH'])
@jwt_required
def update_goal(goal_id):
    """Update a goal (name, category, target_amount, target_date, status). Recalculates levels if amount/date changes."""
    try:
        goal = goal_model.get_goal_by_id(goal_id)
        if not goal:
            return jsonify({"error": "Goal not found"}), 404
        if str(goal['user_id']) != request.user_id:
            return jsonify({"error": "Unauthorized"}), 403

        data = request.json or {}
        allowed = ("goal_name", "goal_category", "target_amount", "target_date", "status")
        update = {k: data[k] for k in allowed if k in data}
        if not update:
            return jsonify({"message": "Nothing to update", "goal": _format_goal(goal)}), 200

        # Check if we need to recalculate levels (if target_amount or target_date changed)
        needs_recalc = ('target_amount' in update and update['target_amount'] != goal['target_amount']) or \
                       ('target_date' in update and update['target_date'] != goal['target_date'])

        goal_model.update_goal(goal_id, update)
        updated = goal_model.get_goal_by_id(goal_id)

        # Recalculate levels with AI if amount or date changed
        if needs_recalc:
            user = user_model.find_by_id(request.user_id)
            monthly_income = 3000
            avg_expenses = 2200

            # Get financial data from bank statements
            try:
                txns = bank_statement_model.get_user_transactions(request.user_id, limit=500)
                if txns:
                    income = sum(float(t.get('amount') or 0) for t in txns if float(t.get('amount') or 0) > 0)
                    expenses = sum(abs(float(t.get('amount') or 0)) for t in txns if float(t.get('amount') or 0) < 0)
                    if income > 0 or expenses > 0:
                        monthly_income = max(1, round(income, 2)) if income > 0 else 3000
                        avg_expenses = round(expenses, 2) if expenses > 0 else 2200
            except Exception:
                pass

            # Recalculate with AI
            ai_result = calculate_levels_with_ai(
                {
                    'target_amount': updated['target_amount'],
                    'current_amount': updated['current_amount'],
                    'category': updated['goal_category'],
                    'target_date': updated.get('target_date')
                },
                {
                    'monthly_income': monthly_income,
                    'avg_expenses': avg_expenses,
                    'current_streak': user.get('current_streak', 0),
                    'from_bank_statement': monthly_income != 3000 or avg_expenses != 2200,
                }
            )

            # Update with new calculations
            goal_model.set_level_system(
                goal_id,
                ai_result['total_levels'],
                ai_result['level_thresholds'],
                ai_result['daily_target']
            )

            updated = goal_model.get_goal_by_id(goal_id)

        return jsonify({"message": "Goal updated", "goal": _format_goal(updated)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/goals/reorder', methods=['POST'])
@jwt_required
def reorder_goals():
    """Set queue order. Body: { "goalIds": ["id1", "id2", ...] } (order = index)."""
    try:
        data = request.json or {}
        goal_ids = data.get("goalIds") or []
        for i, gid in enumerate(goal_ids):
            goal = goal_model.get_goal_by_id(gid)
            if goal and str(goal["user_id"]) == request.user_id:
                goal_model.update_goal(gid, {"order": i})
        goals = goal_model.get_user_goals(request.user_id, exclude_archived=True)
        return jsonify({"goals": [_format_goal(g) for g in goals]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/goals/manifestation', methods=['GET'])
@jwt_required
def get_manifestation_goal():
    """Get the #1 priority goal (lowest order number) to display on dashboard as Active Manifestation."""
    try:
        # Check and update expired goals first
        goal_model.check_expired_goals(request.user_id)

        # Get the manifestation goal (priority #1)
        goal = goal_model.get_manifestation_goal(request.user_id)
        if not goal:
            return jsonify({"goal": None, "message": "No active goals"}), 200

        return jsonify({"goal": _format_goal(goal)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/goals/<goal_id>/archive', methods=['POST'])
@jwt_required
def archive_goal(goal_id):
    """Move a completed or pending goal to archive."""
    try:
        result = goal_model.archive_goal(goal_id, request.user_id)
        if not result:
            return jsonify({"error": "Goal not found or cannot be archived (must be completed or pending)"}), 400

        return jsonify({"message": "Goal archived successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/goals/archived', methods=['GET'])
@jwt_required
def get_archived_goals():
    """Get all archived goals for the current user."""
    try:
        goals = goal_model.get_archived_goals(request.user_id)
        return jsonify({"goals": [_format_goal(g) for g in goals]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/goals/<goal_id>', methods=['DELETE'])
@jwt_required
def delete_goal(goal_id):
    """Delete an archived goal permanently."""
    try:
        deleted = goal_model.delete_goal(goal_id, request.user_id)
        if not deleted:
            return jsonify({"error": "Goal not found or cannot be deleted (must be archived)"}), 400

        return jsonify({"message": "Goal deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/goals/check-expired', methods=['POST'])
@jwt_required
def check_expired_goals():
    """Manually trigger check for expired goals (marks as pending if date passed with $0 saved)."""
    try:
        updated_count = goal_model.check_expired_goals(request.user_id)
        return jsonify({
            "message": f"{updated_count} goal(s) marked as pending",
            "updated_count": updated_count
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _goal_daily_commitment_and_levels(goal):
    """Compute daily commitment and levels 1-50 (amount per level) for a goal."""
    from datetime import datetime
    target = float(goal.get("target_amount", 0) or 0)
    current = float(goal.get("current_amount", 0) or 0)
    remaining = max(0, target - current)
    days = 180
    target_date = goal.get("target_date")
    if target_date:
        try:
            if isinstance(target_date, str):
                target_date = datetime.fromisoformat(target_date.replace("Z", "+00:00"))
            days = max(30, (target_date - datetime.utcnow()).days)
        except Exception:
            pass
    daily_commitment = round(remaining / days, 2) if days else 0
    suggested_levels = min(50, max(1, 50))
    amount_per_level = round(remaining / 50, 2) if remaining else 0
    return {"daily_commitment": daily_commitment, "suggested_levels": 50, "amount_per_level": amount_per_level, "days_to_goal": days}


def _format_goal(g):
    if not g:
        return None
    extra = _goal_daily_commitment_and_levels(g)
    return {
        "_id": str(g["_id"]),
        "user_id": str(g.get("user_id", "")),
        "goal_name": g.get("goal_name", ""),
        "goal_category": g.get("goal_category", "other"),
        "target_amount": g.get("target_amount", 0),
        "current_amount": g.get("current_amount", 0),
        "target_date": g.get("target_date"),
        "total_levels": g.get("total_levels", 10),
        "current_level": g.get("current_level", 0),
        "daily_target": g.get("daily_target", 0),
        "status": g.get("status", "active"),
        "order": g.get("order", 0),
        "completed_at": g.get("completed_at").isoformat() if g.get("completed_at") and hasattr(g.get("completed_at"), "isoformat") else None,
        "daily_commitment": extra["daily_commitment"],
        "suggested_levels": extra["suggested_levels"],
        "amount_per_level": extra["amount_per_level"],
        "days_to_goal": extra["days_to_goal"],
    }


# ============================================================================
# QUESTS: generated from spending (Gemini)
# ============================================================================

@app.route('/api/quests/generated', methods=['GET'])
@jwt_required
def get_generated_quests():
    """Get personalized quest suggestions from hardcoded v4 spending patterns."""
    try:
        goals = goal_model.get_user_goals(request.user_id, status="active")
        goal_name = goals[0].get("goal_name", "") if goals else ""
        quests = get_mock_quests_from_spending(goal_name)
        mock = get_mock_spending_analysis()
        return jsonify({
            "quests": quests,
            "basedOn": {
                "transactionCount": mock["transactionCount"],
                "summary": f"Based on {mock['transactionCount']} transactions from your statement. Quests target your top spending categories.",
            },
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/quests/from-suggestion', methods=['POST'])
@jwt_required
def create_quest_from_suggestion():
    """Create a quest from a suggested (generated) quest and add it to user's active quests. Body: name, description, category, points_reward, currency_reward."""
    try:
        data = request.json or {}
        name = (data.get("name") or "").strip()
        description = (data.get("description") or "").strip()
        category = (data.get("category") or "milestone").strip().lower().replace(" ", "-")
        points_reward = int(data.get("points_reward") or 25)
        currency_reward = int(data.get("currency_reward") or 10)
        if not name:
            return jsonify({"error": "name is required"}), 400
        quest_id = quest_model.create_quest_template(
            name=name,
            description=description,
            category=category,
            points_reward=points_reward,
            currency_reward=currency_reward,
            verification_type="manual",
            duration_hours=24 * 7,
        )
        user_quest_id = quest_model.assign_quest_to_user(request.user_id, quest_id)
        if not user_quest_id:
            return jsonify({"error": "Could not assign quest"}), 500
        return jsonify({
            "message": "Quest added to your tracker",
            "user_quest_id": str(user_quest_id),
            "quest_id": str(quest_id),
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# FRIENDS & NUDGES
# ============================================================================

@app.route('/api/friends', methods=['GET'])
@jwt_required
def get_friends():
    """Get current user's friend list with names/usernames."""
    try:
        user = user_model.find_by_id(request.user_id)
        friend_ids = user.get("friends") or []
        friends = []
        for fid in friend_ids:
            u = user_model.find_by_id(fid)
            if u:
                friends.append({
                    "id": str(u["_id"]),
                    "username": u.get("username", ""),
                    "name": u.get("name", ""),
                })
        return jsonify({"friends": friends}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/friends', methods=['POST'])
@jwt_required
def add_friend():
    """Add a friend by username. Body: { "username": "friend_username" }."""
    try:
        data = request.json or {}
        username = (data.get("username") or "").strip()
        if not username:
            return jsonify({"error": "username is required"}), 400
        friend = user_model.find_by_username(username)
        if not friend:
            return jsonify({"error": "User not found"}), 404
        friend_id = friend["_id"]
        if str(friend_id) == request.user_id:
            return jsonify({"error": "You cannot add yourself"}), 400
        user_model.add_friend(request.user_id, friend_id)
        return jsonify({
            "message": f"Added {friend.get('name') or friend.get('username')} as friend",
            "friend": {"id": str(friend_id), "username": friend.get("username", ""), "name": friend.get("name", "")},
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/nudges', methods=['POST'])
@jwt_required
def send_nudge():
    """Send a nudge to a friend. Body: { "toUserId": "...", "goalId": "...", "goalName": "..." }."""
    try:
        data = request.json or {}
        to_user_id = data.get("toUserId")
        goal_id = data.get("goalId")
        goal_name = (data.get("goalName") or "").strip() or "your goal"

        if not to_user_id:
            return jsonify({"error": "toUserId is required"}), 400

        user = user_model.find_by_id(request.user_id)
        friend_ids = user.get("friends") or []
        from bson import ObjectId
        to_oid = ObjectId(to_user_id)
        if to_oid not in friend_ids and str(to_oid) not in [str(x) for x in friend_ids]:
            return jsonify({"error": "User is not in your friend list"}), 400

        if nudge_model.has_nudged(request.user_id, to_user_id):
            return jsonify({"error": "You can only nudge each friend once."}), 400

        nudge_id = nudge_model.create(request.user_id, to_user_id, goal_id, goal_name)
        to_user = user_model.find_by_id(to_user_id)
        return jsonify({
            "message": f"Sent nudge to {to_user.get('name') or to_user.get('username') or 'friend'}!",
            "nudgeId": str(nudge_id),
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/nudges/sent', methods=['GET'])
@jwt_required
def get_nudges_sent():
    """List of user ids the current user has already nudged (one nudge per friend only)."""
    try:
        ids = nudge_model.get_sent_to_user_ids(request.user_id)
        return jsonify({"sentToUserIds": ids}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/nudges', methods=['GET'])
@jwt_required
def get_my_nudges():
    """Get nudges sent to the current user (for notification: 'X nudged you to keep pushing for your goals!')."""
    try:
        docs = nudge_model.get_for_user(request.user_id, limit=30)
        nudges = []
        for d in docs:
            from_user = user_model.find_by_id(d["from_user_id"])
            nudges.append({
                "id": str(d["_id"]),
                "fromUserId": str(d["from_user_id"]),
                "fromName": (from_user.get("name") or from_user.get("username") or "Someone") if from_user else "Someone",
                "goalName": d.get("goal_name", "your goals"),
                "readAt": d.get("read_at"),
                "createdAt": d.get("created_at"),
            })
        return jsonify({"nudges": nudges}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/nudges/<nudge_id>/read', methods=['POST'])
@jwt_required
def mark_nudge_read(nudge_id):
    """Mark a nudge as read."""
    try:
        nudge_model.mark_read(nudge_id, request.user_id)
        return jsonify({"message": "Marked as read"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# FEED & POSTS
# ============================================================================

def _format_post(post, current_user_id=None):
    """Format post for JSON response with user details and formatted comments"""
    if not post:
        return None

    from bson import ObjectId
    from datetime import datetime

    # Get user details
    user = user_model.find_by_id(post.get("user_id"))
    user_data = {
        "id": str(post.get("user_id")),
        "username": user.get("username", "unknown") if user else "unknown",
        "name": user.get("name", "") if user else "",
        "avatar": (user.get("name", "?")[0].upper() if user and user.get("name") else "👤")
    }

    # Format timestamp
    def _format_timestamp(dt):
        if isinstance(dt, datetime):
            now = datetime.utcnow()
            diff = now - dt
            if diff.days > 0:
                return f"{diff.days}d ago"
            elif diff.seconds // 3600 > 0:
                return f"{diff.seconds // 3600}h ago"
            elif diff.seconds // 60 > 0:
                return f"{diff.seconds // 60}m ago"
            else:
                return "Just now"
        return "Recently"

    created_at = post.get("created_at")
    timestamp = _format_timestamp(created_at)

    # Check if current user liked this post
    likes = post.get("likes", [])
    liked_by_current_user = False
    if current_user_id:
        current_oid = ObjectId(current_user_id) if isinstance(current_user_id, str) else current_user_id
        liked_by_current_user = current_oid in likes

    # Format comments with user details
    comments_list = []
    for comment in post.get("comments", []):
        comment_user_id = comment.get("user_id")
        comment_user = user_model.find_by_id(comment_user_id)

        comments_list.append({
            "user": {
                "id": str(comment_user_id),
                "username": comment_user.get("username", "unknown") if comment_user else "unknown",
                "name": comment_user.get("name", "") if comment_user else "",
                "avatar": (comment_user.get("name", "?")[0].upper() if comment_user and comment_user.get("name") else "👤")
            },
            "text": comment.get("text", ""),
            "timestamp": _format_timestamp(comment.get("created_at")),
            "created_at": comment.get("created_at").isoformat() if isinstance(comment.get("created_at"), datetime) else None
        })

    return {
        "id": str(post["_id"]),
        "user": user_data,
        "content": post.get("content", ""),
        "type": post.get("type", "update"),
        "visibility": post.get("visibility", "public"),
        "likes": len(likes),
        "liked": liked_by_current_user,
        "comments": len(post.get("comments", [])),
        "commentsList": comments_list,
        "timestamp": timestamp,
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else None,
        "metadata": post.get("metadata", {})
    }


@app.route('/api/feed', methods=['GET'])
@jwt_required
def get_feed():
    """Get posts for the user's feed."""
    try:
        feed_type = request.args.get('type', 'all')  # all, friends, own
        limit = int(request.args.get('limit', 50))
        skip = int(request.args.get('skip', 0))

        posts = post_model.get_feed(request.user_id, limit=limit, skip=skip, feed_type=feed_type)

        return jsonify({
            "posts": [_format_post(p, request.user_id) for p in posts]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/posts', methods=['POST'])
@jwt_required
def create_post():
    """Create a new post. Body: { content, type?, visibility?, metadata? }"""
    try:
        data = request.json or {}
        content = (data.get("content") or "").strip()

        if not content:
            return jsonify({"error": "Content is required"}), 400

        if len(content) > 500:
            return jsonify({"error": "Content must be 500 characters or less"}), 400

        post_type = data.get("type", "update")  # update, milestone, achievement, level-up, goal-completed
        visibility = data.get("visibility", "public")  # public, friends-only, private
        metadata = data.get("metadata", {})

        post_id = post_model.create_post(
            user_id=request.user_id,
            content=content,
            post_type=post_type,
            visibility=visibility,
            metadata=metadata
        )

        post = post_model.get_post_by_id(post_id)

        return jsonify({
            "message": "Post created successfully",
            "post": _format_post(post, request.user_id)
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/posts/<post_id>', methods=['GET'])
@jwt_required
def get_post(post_id):
    """Get a specific post by ID."""
    try:
        post = post_model.get_post_by_id(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        return jsonify({"post": _format_post(post, request.user_id)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/posts/<post_id>', methods=['PATCH'])
@jwt_required
def update_post(post_id):
    """Update a post (only by owner). Body: { content }"""
    try:
        post = post_model.get_post_by_id(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        if str(post["user_id"]) != request.user_id:
            return jsonify({"error": "Unauthorized"}), 403

        data = request.json or {}
        content = (data.get("content") or "").strip()

        if not content:
            return jsonify({"error": "Content is required"}), 400

        if len(content) > 500:
            return jsonify({"error": "Content must be 500 characters or less"}), 400

        post_model.update_post(post_id, {"content": content})
        updated_post = post_model.get_post_by_id(post_id)

        return jsonify({
            "message": "Post updated",
            "post": _format_post(updated_post, request.user_id)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/posts/<post_id>', methods=['DELETE'])
@jwt_required
def delete_post(post_id):
    """Delete a post (only by owner)."""
    try:
        deleted = post_model.delete_post(post_id, request.user_id)
        if not deleted:
            return jsonify({"error": "Post not found or unauthorized"}), 404

        return jsonify({"message": "Post deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/posts/<post_id>/like', methods=['POST'])
@jwt_required
def like_post(post_id):
    """Like or unlike a post (toggle)."""
    try:
        result = post_model.like_post(post_id, request.user_id)
        if result is None:
            return jsonify({"error": "Post not found"}), 404

        return jsonify({
            "message": "Liked" if result["liked"] else "Unliked",
            "liked": result["liked"],
            "like_count": result["like_count"]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/posts/<post_id>/comments', methods=['POST'])
@jwt_required
def add_comment(post_id):
    """Add a comment to a post. Body: { text }"""
    try:
        data = request.json or {}
        text = (data.get("text") or "").strip()

        if not text:
            return jsonify({"error": "Comment text is required"}), 400

        if len(text) > 300:
            return jsonify({"error": "Comment must be 300 characters or less"}), 400

        success = post_model.add_comment(post_id, request.user_id, text)
        if not success:
            return jsonify({"error": "Post not found"}), 404

        return jsonify({"message": "Comment added"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/users/<username>/posts', methods=['GET'])
@jwt_required
def get_user_posts(username):
    """Get all posts by a specific user."""
    try:
        user = user_model.find_by_username(username)
        if not user:
            return jsonify({"error": "User not found"}), 404

        limit = int(request.args.get('limit', 50))
        skip = int(request.args.get('skip', 0))

        posts = post_model.get_user_posts(user["_id"], limit=limit, skip=skip)

        return jsonify({
            "posts": [_format_post(p, request.user_id) for p in posts],
            "user": {
                "id": str(user["_id"]),
                "username": user.get("username"),
                "name": user.get("name", "")
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "Gamified Savings API is running"
    }), 200

# ============================================================================
# RUN APP
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
