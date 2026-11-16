import re
from datetime import datetime, date, timedelta
from database import get_db

class LifeAIEngine:
    """
    Intelligent recommendation & natural language assistant engine for LifeAI.
    Combines real-time telemetry from tasks, expenses, habits, and study records
    to generate actionable advice and conversational responses.
    """

    @staticmethod
    def get_user_context(user_id):
        conn = get_db()
        cursor = conn.cursor()
        today_str = date.today().isoformat()

        # 1. User info
        user = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

        # 2. Tasks
        tasks = cursor.execute("""
            SELECT * FROM tasks WHERE user_id = ? ORDER BY 
            CASE priority 
                WHEN 'Urgent' THEN 1 
                WHEN 'High' THEN 2 
                WHEN 'Medium' THEN 3 
                ELSE 4 
            END, due_date ASC
        """, (user_id,)).fetchall()
        
        pending_tasks = [t for t in tasks if t['status'] != 'Completed']
        completed_tasks = [t for t in tasks if t['status'] == 'Completed']
        overdue_tasks = [t for t in pending_tasks if t['due_date'] and t['due_date'] < today_str]
        urgent_tasks = [t for t in pending_tasks if t['priority'] in ('Urgent', 'High')]

        # 3. Expenses
        current_month = date.today().strftime('%Y-%m')
        expenses = cursor.execute("""
            SELECT * FROM expenses 
            WHERE user_id = ? AND date LIKE ?
        """, (user_id, f"{current_month}%")).fetchall()

        total_income = sum(e['amount'] for e in expenses if e['type'] == 'income')
        total_expense = sum(e['amount'] for e in expenses if e['type'] == 'expense')
        budget = user['monthly_budget'] if user and user['monthly_budget'] else 2000.0
        budget_percent = round((total_expense / budget * 100) if budget > 0 else 0, 1)

        # Expense by category
        category_spending = {}
        for e in expenses:
            if e['type'] == 'expense':
                category_spending[e['category']] = category_spending.get(e['category'], 0.0) + e['amount']

        # 4. Habits
        habits = cursor.execute("SELECT * FROM habits WHERE user_id = ?", (user_id,)).fetchall()
        habit_stats = []
        for h in habits:
            # Check today
            done_today = cursor.execute("""
                SELECT completed FROM habit_logs 
                WHERE habit_id = ? AND date = ?
            """, (h['id'], today_str)).fetchone()

            # Calculate current streak
            streak = 0
            check_date = date.today()
            # If not done today, start checking from yesterday to see if active streak
            if not done_today:
                check_date = check_date - timedelta(days=1)
            
            while True:
                log = cursor.execute("""
                    SELECT completed FROM habit_logs 
                    WHERE habit_id = ? AND date = ? AND completed = 1
                """, (h['id'], check_date.isoformat())).fetchone()
                if log:
                    streak += 1
                    check_date = check_date - timedelta(days=1)
                else:
                    break

            habit_stats.append({
                'id': h['id'],
                'name': h['name'],
                'category': h['category'],
                'icon': h['icon'],
                'done_today': bool(done_today and done_today['completed'] == 1),
                'streak': streak
            })

        # 5. Study
        subjects = cursor.execute("SELECT * FROM study_subjects WHERE user_id = ?", (user_id,)).fetchall()
        study_sessions = cursor.execute("""
            SELECT ss.*, sub.name as subject_name 
            FROM study_sessions ss
            LEFT JOIN study_subjects sub ON ss.subject_id = sub.id
            WHERE ss.user_id = ?
        """, (user_id,)).fetchall()
        total_study_minutes = sum(s['duration_minutes'] for s in study_sessions)

        conn.close()

        # Compute Productivity Score (0 - 100)
        # Weights: Tasks (35%), Habits (35%), Budget (15%), Study (15%)
        task_score = (len(completed_tasks) / len(tasks) * 100) if tasks else 80
        if overdue_tasks:
            task_score = max(20, task_score - (len(overdue_tasks) * 15))

        habits_completed_today = sum(1 for h in habit_stats if h['done_today'])
        habit_score = (habits_completed_today / len(habit_stats) * 100) if habit_stats else 80

        budget_score = 100 if budget_percent <= 75 else max(20, 100 - (budget_percent - 75) * 2.5)
        study_score = min(100, (total_study_minutes / 180) * 100) if total_study_minutes else 60

        overall_score = int(round(task_score * 0.35 + habit_score * 0.35 + budget_score * 0.15 + study_score * 0.15))
        overall_score = max(5, min(100, overall_score))

        return {
            'user': user,
            'tasks': tasks,
            'pending_tasks': pending_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'urgent_tasks': urgent_tasks,
            'expenses': expenses,
            'total_income': total_income,
            'total_expense': total_expense,
            'budget': budget,
            'budget_percent': budget_percent,
            'category_spending': category_spending,
            'habits': habit_stats,
            'subjects': subjects,
            'study_sessions': study_sessions,
            'total_study_minutes': total_study_minutes,
            'overall_score': overall_score
        }

    @staticmethod
    def generate_recommendations(user_id):
        ctx = LifeAIEngine.get_user_context(user_id)
        recommendations = []

        # 1. Overdue or Urgent Tasks
        if ctx['overdue_tasks']:
            top_overdue = ctx['overdue_tasks'][0]
            recommendations.append({
                'category': 'tasks',
                'title': f'Action Required: Overdue Task "{top_overdue["title"]}"',
                'description': f'This was scheduled for {top_overdue["due_date"]}. Block 30 minutes to complete or reschedule it today.',
                'action_url': '/tasks',
                'action_text': 'View Task'
            })
        elif ctx['urgent_tasks']:
            top_urgent = ctx['urgent_tasks'][0]
            recommendations.append({
                'category': 'tasks',
                'title': f'Priority Focus: "{top_urgent["title"]}"',
                'description': f'Marked as {top_urgent["priority"]} priority. Tackling your highest-leverage task first will build great momentum today.',
                'action_url': '/tasks',
                'action_text': 'Tackle Now'
            })
        else:
            recommendations.append({
                'category': 'tasks',
                'title': 'All High-Priority Tasks Clear!',
                'description': 'You are currently caught up with urgent tasks. Consider planning ahead or taking a short breather.',
                'action_url': '/tasks',
                'action_text': 'Plan New Task'
            })

        # 2. Habit Tracker Insights
        undone_habits = [h for h in ctx['habits'] if not h['done_today']]
        high_streaks = [h for h in ctx['habits'] if h['streak'] >= 3]
        if undone_habits:
            target_habit = undone_habits[0]
            recommendations.append({
                'category': 'habits',
                'title': f'Keep Streak Alive: {target_habit["name"]}',
                'description': f'You haven\'t logged this habit today. Complete it now to protect your {target_habit["streak"]}-day streak!',
                'action_url': '/habits',
                'action_text': 'Check Off Habit'
            })
        elif high_streaks:
            top_h = max(high_streaks, key=lambda x: x['streak'])
            recommendations.append({
                'category': 'habits',
                'title': f'Habit Mastery: {top_h["streak"]} Days on {top_h["name"]}',
                'description': 'Fantastic consistency! Consistency is turning this action into second nature.',
                'action_url': '/habits',
                'action_text': 'View Streaks'
            })

        # 3. Budget / Financial Health
        if ctx['budget_percent'] > 85:
            recommendations.append({
                'category': 'finance',
                'title': f'Budget Alert: {ctx["budget_percent"]}% Limit Reached',
                'description': f'You have spent ${ctx["total_expense"]:.2f} of your ${ctx["budget"]:.2f} monthly allowance. Limit non-essential spending.',
                'action_url': '/expenses',
                'action_text': 'Audit Expenses'
            })
        else:
            top_cat = None
            if ctx['category_spending']:
                top_cat = max(ctx['category_spending'].items(), key=lambda x: x[1])
            if top_cat:
                recommendations.append({
                    'category': 'finance',
                    'title': f'Spending Trend: {top_cat[0]} is your largest expense',
                    'description': f'You\'ve spent ${top_cat[1]:.2f} on {top_cat[0]} this month ({round(top_cat[1]/ctx["total_expense"]*100 if ctx["total_expense"]>0 else 0)}% of total).',
                    'action_url': '/expenses',
                    'action_text': 'View Breakdown'
                })
            else:
                recommendations.append({
                    'category': 'finance',
                    'title': 'Healthy Cash Flow',
                    'description': f'Budget usage is well controlled at {ctx["budget_percent"]}%. Keep logging your daily coffee and food items.',
                    'action_url': '/expenses',
                    'action_text': 'Log Transaction'
                })

        # 4. Study / Learning
        upcoming_exams = []
        today_date = date.today()
        for s in ctx['subjects']:
            if s['exam_date']:
                try:
                    exam_d = datetime.strptime(s['exam_date'], '%Y-%m-%d').date()
                    days_left = (exam_d - today_date).days
                    if 0 <= days_left <= 30:
                        upcoming_exams.append((s, days_left))
                except Exception:
                    pass
        
        upcoming_exams.sort(key=lambda x: x[1])
        if upcoming_exams:
            sub, days = upcoming_exams[0]
            recommendations.append({
                'category': 'study',
                'title': f'Exam in {days} Days: {sub["name"]}',
                'description': f'Use the built-in Pomodoro timer to complete a 25-minute active recall study block today.',
                'action_url': '/study',
                'action_text': 'Start Pomodoro'
            })
        else:
            recommendations.append({
                'category': 'study',
                'title': 'Deep Work Focus Time',
                'description': 'A 25-minute Pomodoro session boosts retention and focus by 40%. Start a session now.',
                'action_url': '/study',
                'action_text': 'Launch Timer'
            })

        return recommendations

    @staticmethod
    def process_chat_message(user_id, message_text):
        """
        Processes natural language user requests, can execute quick actions
        (like adding tasks or expenses) and answers queries intelligently.
        """
        text = message_text.strip()
        lower = text.lower()
        conn = get_db()
        cursor = conn.cursor()
        ctx = LifeAIEngine.get_user_context(user_id)

        # 1. Action: Quick Add Task via Chat
        # Examples: "add task Finish paper tomorrow urgent", "new task buy milk"
        task_match = re.search(r'^(?:add\s+task|new\s+task|create\s+task)[:\s]+(.+)$', text, re.IGNORECASE)
        if task_match:
            raw_task = task_match.group(1).strip()
            # Extract priority if mentioned
            priority = 'Medium'
            if 'urgent' in raw_task.lower():
                priority = 'Urgent'
                raw_task = re.sub(r'\burgent\b', '', raw_task, flags=re.IGNORECASE).strip()
            elif 'high' in raw_task.lower():
                priority = 'High'
                raw_task = re.sub(r'\bhigh\b', '', raw_task, flags=re.IGNORECASE).strip()
            elif 'low' in raw_task.lower():
                priority = 'Low'
                raw_task = re.sub(r'\blow\b', '', raw_task, flags=re.IGNORECASE).strip()

            # Extract due date
            due_date = date.today().isoformat()
            if 'tomorrow' in raw_task.lower():
                due_date = (date.today() + timedelta(days=1)).isoformat()
                raw_task = re.sub(r'\btomorrow\b', '', raw_task, flags=re.IGNORECASE).strip()
            elif 'today' in raw_task.lower():
                due_date = date.today().isoformat()
                raw_task = re.sub(r'\btoday\b', '', raw_task, flags=re.IGNORECASE).strip()

            cursor.execute("""
                INSERT INTO tasks (user_id, title, description, category, priority, due_date, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Pending')
            """, (user_id, raw_task, "Added via LifeAI Chat Assistant", "General", priority, due_date))
            conn.commit()
            conn.close()
            return f"✅ **Task Added Successfully!**\n- **Title:** {raw_task}\n- **Priority:** {priority}\n- **Due Date:** {due_date}\n\nYou can view and manage it anytime in your [Tasks](/tasks) page."

        # 2. Action: Quick Add Expense via Chat
        # Examples: "add expense $25 lunch", "spend 14.50 coffee", "log expense 10 snacks"
        expense_match = re.search(r'(?:add\s+expense|log\s+expense|spent|spend)\s*[:\-]?\s*\$?([0-9]+(?:\.[0-9]+)?)\s*(?:for|on)?\s*(.+)', text, re.IGNORECASE)
        if expense_match:
            amount = float(expense_match.group(1))
            desc = expense_match.group(2).strip()
            category = 'Food' if any(w in desc.lower() for w in ['coffee', 'lunch', 'dinner', 'breakfast', 'food', 'snack', 'grocery']) else \
                       'Transport' if any(w in desc.lower() for w in ['uber', 'bus', 'train', 'gas', 'metro', 'fuel']) else \
                       'Entertainment' if any(w in desc.lower() for w in ['movie', 'game', 'concert', 'netflix']) else 'Other'

            cursor.execute("""
                INSERT INTO expenses (user_id, title, amount, type, category, date, notes)
                VALUES (?, ?, ?, 'expense', ?, ?, 'Logged via LifeAI Chat')
            """, (user_id, desc.capitalize(), amount, category, date.today().isoformat()))
            conn.commit()
            conn.close()
            return f"💳 **Expense Recorded!**\n- **Amount:** ${amount:.2f}\n- **Description:** {desc.capitalize()}\n- **Category:** {category}\n\nYour updated monthly expenses are now reflected in [Expenses & Budget](/expenses)."

        # 3. Action: Complete Habit via Chat
        # Examples: "completed habit meditation", "did drink water"
        if any(w in lower for w in ['completed habit', 'did habit', 'done with habit', 'log habit']):
            for h in ctx['habits']:
                if h['name'].lower() in lower or any(word in lower for word in h['name'].lower().split() if len(word) > 3):
                    cursor.execute("""
                        INSERT OR REPLACE INTO habit_logs (habit_id, user_id, date, completed)
                        VALUES (?, ?, ?, 1)
                    """, (h['id'], user_id, date.today().isoformat()))
                    conn.commit()
                    conn.close()
                    return f"🔥 **Awesome!** I've marked **{h['name']}** as completed for today. Current streak is now **{h['streak'] + (0 if h['done_today'] else 1)} days**! Keep up the momentum!"

        # 4. Contextual Query: Tasks Status & Planning
        if any(w in lower for w in ['task', 'to do', 'todo', 'focus', 'priority', 'what should i do']):
            if ctx['pending_tasks']:
                lines = [f"📋 **You currently have {len(ctx['pending_tasks'])} pending tasks.** Here are the top priorities:"]
                for idx, t in enumerate(ctx['pending_tasks'][:4], 1):
                    badge = "🔥 [Urgent]" if t['priority'] == 'Urgent' else ("⚡ [High]" if t['priority'] == 'High' else "")
                    due = f" (Due: {t['due_date']})" if t['due_date'] else ""
                    lines.append(f"{idx}. **{t['title']}** {badge}{due}")
                
                lines.append("\n💡 **Recommendation:** Start with the first high-priority task using a 25-minute Pomodoro session. Type `add task <title>` anytime to add more.")
                conn.close()
                return "\n".join(lines)
            else:
                conn.close()
                return "🎉 **Zero pending tasks!** You've completed everything on your list. Would you like to set new goals or plan upcoming projects?"

        # 5. Contextual Query: Spending, Budget & Expenses
        if any(w in lower for w in ['expense', 'spend', 'budget', 'money', 'finance', 'cost']):
            rem = ctx['budget'] - ctx['total_expense']
            status_text = "healthy" if ctx['budget_percent'] < 80 else "approaching limit"
            resp = f"💰 **Financial Snapshot for {date.today().strftime('%B %Y')}:**\n"
            resp += f"- **Total Spent:** ${ctx['total_expense']:.2f} ({ctx['budget_percent']}% of ${ctx['budget']:.2f} budget)\n"
            resp += f"- **Remaining Budget:** ${rem:.2f}\n"
            resp += f"- **Monthly Income:** ${ctx['total_income']:.2f}\n"
            if ctx['category_spending']:
                top_cats = sorted(ctx['category_spending'].items(), key=lambda x: x[1], reverse=True)[:3]
                resp += "\n**Top Spending Categories:**\n"
                for cat, amt in top_cats:
                    resp += f"- {cat}: ${amt:.2f}\n"
            resp += f"\nYour budget pace is currently **{status_text}**. You can quickly log expenses by typing `add expense $15 Coffee`."
            conn.close()
            return resp

        # 6. Contextual Query: Habits & Streaks
        if any(w in lower for w in ['habit', 'streak', 'routine', 'consistency']):
            if ctx['habits']:
                resp = "🌱 **Your Daily Habits Overview:**\n"
                for h in ctx['habits']:
                    status = "✅ Done" if h['done_today'] else "⏳ Pending"
                    resp += f"- **{h['name']}**: {status} (Streak: {h['streak']} days)\n"
                pending_count = sum(1 for h in ctx['habits'] if not h['done_today'])
                if pending_count > 0:
                    resp += f"\nYou have {pending_count} habit(s) remaining for today. Completing them will elevate your daily productivity score!"
                else:
                    resp += "\n🌟 Outstanding! All your habits are completed for today!"
                conn.close()
                return resp
            else:
                conn.close()
                return "You haven't set up any habits yet! Head over to the [Habit Tracker](/habits) to add daily routines like Meditation, Reading, or Exercise."

        # 7. Contextual Query: Study & Exams
        if any(w in lower for w in ['study', 'exam', 'pomodoro', 'learn', 'subject', 'school']):
            resp = f"📚 **Study & Learning Progress:**\n"
            resp += f"- **Total Study Time Logged:** {ctx['total_study_minutes']} minutes (~{ctx['total_study_minutes']//60}h {ctx['total_study_minutes']%60}m)\n"
            if ctx['subjects']:
                resp += "- **Registered Subjects:**\n"
                for s in ctx['subjects']:
                    exam_info = f" (Exam: {s['exam_date']})" if s['exam_date'] else ""
                    resp += f"  • {s['name']}{exam_info} - Target: {s['target_hours']}h\n"
            resp += "\n⚡ **Pro-tip:** Use the interactive [Study Planner](/study) with the integrated Pomodoro Timer to maintain maximum mental endurance without burnout."
            conn.close()
            return resp

        # 8. Productivity / Score Audit
        if any(w in lower for w in ['score', 'productivity', 'how am i doing', 'summary', 'audit', 'daily overview']):
            score = ctx['overall_score']
            grade = "A+ (Peak Flow)" if score >= 85 else ("B+ (Strong Progress)" if score >= 70 else "C (Room for Growth)")
            resp = f"⚡ **LifeAI Daily Life Audit**\n"
            resp += f"- **Overall Score:** {score}/100 ({grade})\n"
            resp += f"- **Pending Tasks:** {len(ctx['pending_tasks'])}\n"
            resp += f"- **Budget Utilization:** {ctx['budget_percent']}%\n"
            resp += f"- **Habits Completed Today:** {sum(1 for h in ctx['habits'] if h['done_today'])} / {len(ctx['habits'])}\n\n"
            resp += "Check the [Recommendations](/recommendations) page for personalized action steps generated specifically for you!"
            conn.close()
            return resp

        # 9. General life advice, motivation, time-management tips
        conn.close()
        return (
            f"I hear you! As your LifeAI assistant, here is a practical recommendation:\n\n"
            f"1. **Eat the Frog:** Identify your single hardest task today (`{ctx['pending_tasks'][0]['title'] if ctx['pending_tasks'] else 'your core priority'}`) and work on it uninterrupted for 25 minutes.\n"
            f"2. **Protect Your Habits:** Consistency is compound interest for personal growth. Even doing 2 minutes of a habit maintains the neural pathway.\n"
            f"3. **Mindful Spending:** Before non-essential purchases, apply the 48-hour rule to verify true necessity.\n\n"
            f"You can ask me anything about your schedule, or tell me `add task <title>`, `add expense $<amount> <desc>`, or `status`!"
        )
