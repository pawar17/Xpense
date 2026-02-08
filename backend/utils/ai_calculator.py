import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

_api_key = os.getenv('GOOGLE_AI_API_KEY')
if _api_key and _api_key.strip() and _api_key.strip() not in ('your_google_ai_api_key', 'your_google_ai_key'):
    genai.configure(api_key=_api_key.strip())

# Current Gemini model IDs (see https://ai.google.dev/gemini-api/docs/models)
GEMINI_CHAT_MODEL = "gemini-2.0-flash"
GEMINI_CHAT_FALLBACK = "gemini-2.5-flash"
GEMINI_GOAL_MODEL = "gemini-2.0-flash"

def calculate_levels_with_ai(goal_data, user_data=None):
    """
    Calculate optimal savings levels using AI with sophisticated financial analysis.
    Uses Gemini to determine:
    - Appropriate number of levels based on goal size and complexity
    - Realistic daily contribution based on actual income and expenses
    Falls back to basic calculation if AI fails
    """
    if user_data is None:
        user_data = {}

    # Basic fallback calculation
    remaining = goal_data['target_amount'] - goal_data.get('current_amount', 0)
    current = goal_data.get('current_amount', 0)

    # Calculate days to goal
    days_to_goal = 180
    if goal_data.get('target_date'):
        target_date = goal_data['target_date']
        if isinstance(target_date, str):
            target_date = datetime.fromisoformat(target_date.replace('Z', '+00:00'))
        days_to_goal = max((target_date - datetime.utcnow()).days, 30)

    monthly_income = user_data.get('monthly_income') or 3000
    avg_expenses = user_data.get('avg_expenses') or 2200
    from_statement = user_data.get('from_bank_statement', False)

    # Calculate disposable income
    monthly_disposable = max(0, monthly_income - avg_expenses)
    daily_disposable = round(monthly_disposable / 30, 2)

    # Default level count by remaining amount (fallback)
    if remaining < 500:
        total_levels = 10
    elif remaining < 2000:
        total_levels = 20
    elif remaining < 5000:
        total_levels = 30
    else:
        total_levels = 50

    amount_per_level = remaining / total_levels
    level_thresholds = [
        current + (amount_per_level * i)
        for i in range(1, total_levels + 1)
    ]
    daily_target = round(remaining / days_to_goal, 2)

    # Try AI enhancement (Gemini): Use sophisticated analysis for levels and daily target
    try:
        prompt = f"""
You are an expert financial advisor analyzing a user's savings goal. Based on their actual financial data and the goal characteristics, calculate the optimal savings plan.

FINANCIAL DATA (from bank statement):
- Monthly income: ${monthly_income}
- Monthly expenses: ${avg_expenses}
- Disposable income per month: ${monthly_disposable}
- Disposable income per day: ${daily_disposable}
- Data from actual bank statement: {from_statement}
- Current savings streak: {user_data.get('current_streak', 0)} days

GOAL DETAILS:
- Goal name/category: {goal_data.get('category', 'general')}
- Target amount: ${goal_data['target_amount']}
- Current saved: ${current}
- Remaining to save: ${remaining}
- Days until deadline: {days_to_goal}
- Simple math (remaining/days): ${round(remaining / days_to_goal, 2)}/day

YOUR TASK:
1. Determine the appropriate number of levels (5-50) based on goal COMPLEXITY and SIZE:
   - Small items like jackets, accessories, gadgets: 5-10 levels (achievable quickly)
   - Medium items like laptops, trips, furniture: 15-25 levels (moderate motivation)
   - Large items like cars, down payments: 30-40 levels (sustained effort)
   - Major items like houses, large investments: 45-50 levels (long-term commitment)

   The NUMBER OF LEVELS should match the psychological complexity and time commitment of the goal.
   A $50,000 house down payment MUST have 45-50 levels. A $50 jacket MUST have 5-10 levels.

2. Calculate a REALISTIC daily contribution that:
   - Fits within their disposable income (${daily_disposable}/day available)
   - Reaches the goal by the deadline ({days_to_goal} days)
   - Accounts for unexpected expenses (leave some buffer)
   - Is achievable and sustainable (not too aggressive)

3. If the goal is mathematically impossible (requires more than disposable income), suggest the maximum sustainable amount.

4. Provide motivational messages tailored to the goal type.

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "suggested_total_levels": <number 5-50>,
  "suggested_daily_target": <realistic dollar amount>,
  "is_achievable": <true/false>,
  "daily_savings_tip": "<specific actionable tip, max 80 chars>",
  "milestone_message_25": "<motivational message, max 50 chars>",
  "milestone_message_50": "<motivational message, max 50 chars>",
  "milestone_message_75": "<motivational message, max 50 chars>",
  "completion_message": "<celebration message, max 50 chars>",
  "financial_analysis": "<brief explanation of the calculation>"
}}

Example for a $50 jacket goal:
{{"suggested_total_levels": 8, "suggested_daily_target": 2.50, "is_achievable": true, "daily_savings_tip": "Skip one coffee this week", "milestone_message_25": "Great start!", "milestone_message_50": "Halfway there!", "milestone_message_75": "Almost yours!", "completion_message": "Time to shop!", "financial_analysis": "Small purchase, 8 levels keeps it simple and achievable within 20 days at $2.50/day"}}

Example for a $40,000 house down payment:
{{"suggested_total_levels": 50, "suggested_daily_target": 45.00, "is_achievable": true, "daily_savings_tip": "Review subscriptions, cook at home 4x/week", "milestone_message_25": "Building your future!", "milestone_message_50": "Halfway to homeownership!", "milestone_message_75": "Your dream is close!", "completion_message": "Welcome home!", "financial_analysis": "Major goal requires 50 levels for sustained motivation. At $45/day with ${daily_disposable}/day disposable, achievable in {days_to_goal} days with discipline"}}
"""

        model = genai.GenerativeModel(GEMINI_GOAL_MODEL)
        response = model.generate_content(prompt)

        ai_text = response.text.strip()
        # Clean up markdown code blocks
        if '```json' in ai_text:
            ai_text = ai_text.split('```json')[1].split('```')[0].strip()
        elif '```' in ai_text:
            ai_text = ai_text.split('```')[1].split('```')[0].strip()

        ai_data = json.loads(ai_text)

        # Use AI-suggested levels if valid
        sug_levels = ai_data.get('suggested_total_levels')
        if isinstance(sug_levels, (int, float)) and 5 <= int(sug_levels) <= 50:
            total_levels = int(sug_levels)
            amount_per_level = remaining / total_levels
            level_thresholds = [current + (amount_per_level * i) for i in range(1, total_levels + 1)]

        # Use AI-suggested daily target
        sug_daily = ai_data.get('suggested_daily_target')
        if isinstance(sug_daily, (int, float)) and float(sug_daily) >= 0:
            daily_target = round(float(sug_daily), 2)

        return {
            'total_levels': total_levels,
            'level_thresholds': level_thresholds,
            'daily_target': daily_target,
            'ai_suggestions': {k: v for k, v in ai_data.items() if k not in ('suggested_total_levels', 'suggested_daily_target')}
        }

    except Exception as e:
        print(f"AI calculation failed: {e}, using fallback")
        return {
            'total_levels': total_levels,
            'level_thresholds': level_thresholds,
            'daily_target': daily_target,
            'ai_suggestions': {
                'daily_savings_tip': f"Save ${daily_target} per day to reach your goal",
                'milestone_message_25': "Quarter way there! Keep going!",
                'milestone_message_50': "Halfway done! You're crushing it!",
                'milestone_message_75': "Almost there! Sprint to the finish!",
                'completion_message': "Goal achieved! Time to celebrate!",
                'is_achievable': daily_target <= daily_disposable * 0.8 if daily_disposable > 0 else True,
                'financial_analysis': f"Standard calculation: ${daily_target}/day over {days_to_goal} days"
            }
        }

def calculate_multiple_goals_with_ai(goals_data, user_data=None):
    """
    Calculate daily contributions for multiple goals simultaneously.
    Uses Gemini to intelligently allocate disposable income across goals based on:
    - Priority (deadline urgency)
    - Goal size and complexity
    - Available financial capacity

    Returns a dict with per-goal recommendations.
    """
    if user_data is None:
        user_data = {}

    if not goals_data or len(goals_data) == 0:
        return {}

    # If only one goal, use the single-goal function
    if len(goals_data) == 1:
        result = calculate_levels_with_ai(goals_data[0], user_data)
        return {goals_data[0].get('goal_id', 0): result}

    monthly_income = user_data.get('monthly_income') or 3000
    avg_expenses = user_data.get('avg_expenses') or 2200
    from_statement = user_data.get('from_bank_statement', False)

    # Calculate disposable income
    monthly_disposable = max(0, monthly_income - avg_expenses)
    daily_disposable = round(monthly_disposable / 30, 2)

    # Prepare goals summary for Gemini
    goals_summary = []
    for i, goal in enumerate(goals_data):
        remaining = goal['target_amount'] - goal.get('current_amount', 0)
        days_to_goal = 180
        if goal.get('target_date'):
            target_date = goal['target_date']
            if isinstance(target_date, str):
                target_date = datetime.fromisoformat(target_date.replace('Z', '+00:00'))
            days_to_goal = max((target_date - datetime.utcnow()).days, 30)

        goals_summary.append({
            'id': i,
            'name': goal.get('goal_name', 'Goal'),
            'category': goal.get('category', 'general'),
            'target': goal['target_amount'],
            'current': goal.get('current_amount', 0),
            'remaining': remaining,
            'days': days_to_goal
        })

    try:
        prompt = f"""
You are a financial advisor helping a user save for MULTIPLE goals simultaneously. Analyze their financial capacity and intelligently allocate daily contributions across all goals.

FINANCIAL CAPACITY:
- Monthly income: ${monthly_income}
- Monthly expenses: ${avg_expenses}
- Disposable income per month: ${monthly_disposable}
- Disposable income per day: ${daily_disposable}
- Data from bank statement: {from_statement}

GOALS TO MANAGE:
{json.dumps(goals_summary, indent=2)}

YOUR TASK:
1. For EACH goal, determine:
   a) Number of levels (5-50) based on goal size and complexity
      - Small items (< $500): 5-10 levels
      - Medium items ($500-$5,000): 15-25 levels
      - Large items ($5,000-$20,000): 30-40 levels
      - Major items (> $20,000): 45-50 levels

   b) Realistic daily contribution that:
      - When SUMMED across ALL goals, fits within ${daily_disposable}/day
      - Prioritizes urgent goals (fewer days remaining)
      - Ensures all goals can be completed by their deadlines if possible
      - Leaves some buffer (use max 80% of disposable income)

2. If total required contributions exceed capacity, prioritize by deadline and adjust.

3. Return suggestions for each goal with motivational messages.

Return ONLY valid JSON (no markdown):
{{
  "total_daily_allocation": <sum of all daily targets>,
  "is_feasible": <true/false - can all goals be met?>,
  "overall_tip": "<advice for managing multiple goals, max 100 chars>",
  "goals": [
    {{
      "id": <goal id from input>,
      "suggested_total_levels": <5-50>,
      "suggested_daily_target": <realistic amount>,
      "priority_rank": <1 for highest priority>,
      "daily_savings_tip": "<specific tip, max 80 chars>",
      "milestone_message_25": "<message, max 50 chars>",
      "milestone_message_50": "<message, max 50 chars>",
      "milestone_message_75": "<message, max 50 chars>",
      "completion_message": "<message, max 50 chars>"
    }}
  ]
}}
"""

        model = genai.GenerativeModel(GEMINI_GOAL_MODEL)
        response = model.generate_content(prompt)

        ai_text = response.text.strip()
        if '```json' in ai_text:
            ai_text = ai_text.split('```json')[1].split('```')[0].strip()
        elif '```' in ai_text:
            ai_text = ai_text.split('```')[1].split('```')[0].strip()

        ai_data = json.loads(ai_text)

        # Process results for each goal
        results = {}
        for goal_result in ai_data.get('goals', []):
            goal_id = goal_result.get('id')
            if goal_id is None or goal_id >= len(goals_data):
                continue

            goal = goals_data[goal_id]
            remaining = goal['target_amount'] - goal.get('current_amount', 0)
            current = goal.get('current_amount', 0)

            total_levels = goal_result.get('suggested_total_levels', 20)
            total_levels = max(5, min(50, int(total_levels)))

            amount_per_level = remaining / total_levels
            level_thresholds = [current + (amount_per_level * i) for i in range(1, total_levels + 1)]

            daily_target = round(float(goal_result.get('suggested_daily_target', 0)), 2)

            results[goal.get('goal_id', goal_id)] = {
                'total_levels': total_levels,
                'level_thresholds': level_thresholds,
                'daily_target': daily_target,
                'priority_rank': goal_result.get('priority_rank', goal_id + 1),
                'ai_suggestions': {
                    'daily_savings_tip': goal_result.get('daily_savings_tip', 'Stay focused on your goal'),
                    'milestone_message_25': goal_result.get('milestone_message_25', 'Great progress!'),
                    'milestone_message_50': goal_result.get('milestone_message_50', 'Halfway there!'),
                    'milestone_message_75': goal_result.get('milestone_message_75', 'Almost done!'),
                    'completion_message': goal_result.get('completion_message', 'Goal achieved!'),
                    'is_feasible': ai_data.get('is_feasible', True),
                    'overall_tip': ai_data.get('overall_tip', 'Focus on one goal at a time'),
                    'total_daily_allocation': ai_data.get('total_daily_allocation', 0)
                }
            }

        return results

    except Exception as e:
        print(f"Multi-goal AI calculation failed: {e}, using individual calculations")
        # Fallback: calculate each goal individually
        results = {}
        for i, goal in enumerate(goals_data):
            result = calculate_levels_with_ai(goal, user_data)
            results[goal.get('goal_id', i)] = result
        return results


def _is_google_ai_configured():
    key = os.getenv('GOOGLE_AI_API_KEY') or ''
    key = key.strip()
    return key and key not in ('your_google_ai_api_key', 'your_google_ai_key')


def ai_chat_assistant(user_message, user_context):
    """
    AI chatbot that teaches finance concepts (down payments, emergency fund, APR, etc.)
    for the SavePop savings app.
    """
    if not _is_google_ai_configured():
        return (
            "To use the finance coach, add your Google AI (Gemini) API key in the backend .env file as GOOGLE_AI_API_KEY. "
            "Until then, here’s a quick tip: a down payment is the upfront cash you pay when buying something big (like a car or house); "
            "the rest you borrow. Saving for it first helps you pay less interest and get better terms."
        )

    try:
        prompt = f"""
You are SavePop's friendly finance coach. Your main job is to teach personal finance concepts in simple, short ways so users can learn while they save.

You love explaining things like:
- Down payment (what it is, why it matters, typical ranges like 10–20% for cars, 10–20% for homes)
- Emergency fund (3–6 months of expenses, why it’s first)
- APR and interest (how borrowing costs work in plain language)
- Budgeting, saving goals, and good money habits

User context (use only to personalize, not required for teaching):
- Name: {user_context.get('name', 'there')}
- Current goal: {user_context.get('goal_name', 'No active goal')}
- Progress: ${user_context.get('current_amount', 0)} / ${user_context.get('target_amount', 0)} ({user_context.get('progress_percent', 0)}%)
- Streak: {user_context.get('current_streak', 0)} days

User asked: "{user_message}"

Rules:
- Do not start with greetings (no Hi, Hey there, or the user's name)—go straight to the answer.
- Answer in 2–4 short sentences. Be clear and encouraging.
- Use simple words. If you use a term (e.g. APR), briefly define it.
- You may use 1–2 emojis if it fits. Stay focused on teaching the concept.
- If they ask something off-topic, gently steer to a related finance idea or say you’re here for finance and savings.
"""

        for model_name in (GEMINI_CHAT_MODEL, GEMINI_CHAT_FALLBACK):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                text = (response.text or "").strip()
                if text:
                    return text
            except Exception as fallback_e:
                print(f"AI chat failed with {model_name}: {fallback_e}")
                continue
        return "Ask me about down payments, emergency funds, APR, or saving tips!"

    except Exception as e:
        err = str(e).lower()
        print(f"AI chat failed: {e}")
        if 'api_key' in err or 'invalid' in err or '403' in err or '401' in err:
            return (
                "Google AI rejected the request. Check that GOOGLE_AI_API_KEY in backend/.env "
                "is a valid key from https://aistudio.google.com and restart the backend."
            )
        return "I'm having trouble connecting right now. Try again in a bit—and remember: a down payment is the chunk you pay upfront so you borrow less and pay less interest!"
