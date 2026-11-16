from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from datetime import datetime, date, timedelta
from database import get_db, init_db, seed_demo_user_if_needed, populate_user_starter_data
from ai_engine import LifeAIEngine

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'lifeai-super-secret-key-2026')
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize database and demo user on startup
init_db()
seed_demo_user_if_needed()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access your LifeAI dashboard.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user():
    """Injects current user and notifications into all templates."""
    if 'user_id' in session:
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        conn.close()
        return {'current_user': user}
    return {'current_user': None}

# ----------------- AUTHENTICATION -----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        user = conn.execute("""
            SELECT * FROM users 
            WHERE username = ? OR email = ?
        """, (login_input, login_input)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['theme'] = user['theme']
            flash(f"Welcome back, {user['full_name']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        with_starter_data = request.form.get('starter_data', 'on') == 'on'

        if not username or not email or not password or not full_name:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html')

        conn = get_db()
        cursor = conn.cursor()

        existing = cursor.execute("""
            SELECT id FROM users WHERE username = ? OR email = ?
        """, (username, email)).fetchone()

        if existing:
            conn.close()
            flash('Username or Email already registered. Please login.', 'danger')
            return render_template('register.html')

        pwd_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, monthly_budget, theme)
            VALUES (?, ?, ?, ?, 2500.0, 'dark')
        """, (username, email, pwd_hash, full_name))
        new_user_id = cursor.lastrowid
        conn.commit()

        if with_starter_data:
            populate_user_starter_data(new_user_id, conn)

        conn.close()

        session['user_id'] = new_user_id
        session['username'] = username
        session['theme'] = 'dark'
        flash('Account created successfully! Welcome to LifeAI.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('login'))

# ----------------- DASHBOARD -----------------

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    ctx = LifeAIEngine.get_user_context(user_id)
    recs = LifeAIEngine.generate_recommendations(user_id)

    # Days of current week for habit quick bar
    today = date.today()
    week_days = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        week_days.append({
            'date': d.isoformat(),
            'name': d.strftime('%a'),
            'day': d.strftime('%d'),
            'is_today': (d == today)
        })

    # Prepare chart data for expenses
    cat_labels = list(ctx['category_spending'].keys())
    cat_values = list(ctx['category_spending'].values())

    return render_template(
        'dashboard.html',
        ctx=ctx,
        recommendations=recs,
        week_days=week_days,
        cat_labels=cat_labels,
        cat_values=cat_values
    )

# ----------------- TASK MANAGER -----------------

@app.route('/tasks')
@login_required
def tasks():
    user_id = session['user_id']
    conn = get_db()
    all_tasks = conn.execute("""
        SELECT * FROM tasks 
        WHERE user_id = ? 
        ORDER BY 
            status ASC,
            CASE priority 
                WHEN 'Urgent' THEN 1 
                WHEN 'High' THEN 2 
                WHEN 'Medium' THEN 3 
                ELSE 4 
            END,
            due_date ASC
    """, (user_id,)).fetchall()
    conn.close()

    today_str = date.today().isoformat()
    return render_template('tasks.html', tasks=all_tasks, today=today_str)

@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    user_id = session['user_id']
    data = request.get_json() if request.is_json else request.form

    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': 'Task title is required'}), 400

    description = data.get('description', '').strip()
    category = data.get('category', 'Work')
    priority = data.get('priority', 'Medium')
    due_date = data.get('due_date', '')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (user_id, title, description, category, priority, due_date, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending')
    """, (user_id, title, description, category, priority, due_date))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()

    if request.is_json:
        return jsonify({'success': True, 'id': task_id, 'message': 'Task created successfully'})
    flash('Task added successfully!', 'success')
    return redirect(url_for('tasks'))

@app.route('/api/tasks/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    task = cursor.execute("SELECT status FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)).fetchone()
    if not task:
        conn.close()
        return jsonify({'error': 'Task not found'}), 404

    new_status = 'Pending' if task['status'] == 'Completed' else 'Completed'
    cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'new_status': new_status})

@app.route('/api/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    user_id = session['user_id']
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.commit()
    conn.close()
    if request.is_json:
        return jsonify({'success': True})
    flash('Task deleted.', 'info')
    return redirect(url_for('tasks'))

@app.route('/api/tasks/ai-breakdown', methods=['POST'])
@login_required
def ai_breakdown():
    data = request.get_json() or {}
    task_title = data.get('title', '').strip()
    if not task_title:
        return jsonify({'error': 'Title required'}), 400

    # Intelligent algorithmic decomposition of tasks into actionable subtasks
    lower = task_title.lower()
    subtasks = []

    if any(w in lower for w in ['study', 'exam', 'paper', 'research', 'homework', 'presentation']):
        subtasks = [
            f"Phase 1: Outline core objectives & gather reference notes for {task_title}",
            "Phase 2: Draft main content / solve practice problem sets (25m Pomodoro)",
            "Phase 3: Review critical formulas and create revision flashcards",
            "Phase 4: Final proofreading and simulated rehearsal"
        ]
    elif any(w in lower for w in ['code', 'build', 'app', 'website', 'api', 'bug', 'feature']):
        subtasks = [
            f"Step 1: Define architecture & database schema for {task_title}",
            "Step 2: Implement core backend logic and endpoints",
            "Step 3: Construct responsive UI components & forms",
            "Step 4: Execute testing, edge-case verification, and clean up"
        ]
    elif any(w in lower for w in ['workout', 'gym', 'run', 'diet', 'fitness']):
        subtasks = [
            "Warm-up: 5 minutes dynamic stretching & mobility",
            "Main Focus: 3 sets of compound movements or cardio intervals",
            "Cool-down: 5 minutes slow pacing & hydration",
            "Log metrics and nutrition in LifeAI"
        ]
    else:
        subtasks = [
            f"Clarify scope and end deliverables for '{task_title}'",
            "Gather all required tools, files, or resources",
            "Execute main work in an uninterrupted 30-minute sprint",
            "Final quality check and mark complete"
        ]

    return jsonify({'success': True, 'subtasks': subtasks})

# ----------------- EXPENSE TRACKER -----------------

@app.route('/expenses')
@login_required
def expenses():
    user_id = session['user_id']
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    
    current_month = date.today().strftime('%Y-%m')
    all_expenses = conn.execute("""
        SELECT * FROM expenses 
        WHERE user_id = ? 
        ORDER BY date DESC, id DESC
    """, (user_id,)).fetchall()
    conn.close()

    month_expenses = [e for e in all_expenses if e['date'].startswith(current_month)]
    total_income = sum(e['amount'] for e in month_expenses if e['type'] == 'income')
    total_expense = sum(e['amount'] for e in month_expenses if e['type'] == 'expense')
    net_savings = total_income - total_expense
    budget = user['monthly_budget'] if user and user['monthly_budget'] else 2500.0
    budget_usage = round((total_expense / budget * 100) if budget > 0 else 0, 1)

    # Category breakdown
    cat_breakdown = {}
    for e in month_expenses:
        if e['type'] == 'expense':
            cat_breakdown[e['category']] = cat_breakdown.get(e['category'], 0.0) + e['amount']

    return render_template(
        'expenses.html',
        expenses=all_expenses,
        total_income=total_income,
        total_expense=total_expense,
        net_savings=net_savings,
        budget=budget,
        budget_usage=budget_usage,
        cat_breakdown=cat_breakdown,
        today=date.today().isoformat()
    )

@app.route('/api/expenses', methods=['POST'])
@login_required
def add_expense():
    user_id = session['user_id']
    data = request.get_json() if request.is_json else request.form

    title = data.get('title', '').strip()
    amount = float(data.get('amount', 0))
    exp_type = data.get('type', 'expense')
    category = data.get('category', 'Other')
    date_str = data.get('date', date.today().isoformat())
    notes = data.get('notes', '').strip()

    if not title or amount <= 0:
        if request.is_json:
            return jsonify({'error': 'Valid title and positive amount required'}), 400
        flash('Valid title and amount required.', 'danger')
        return redirect(url_for('expenses'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO expenses (user_id, title, amount, type, category, date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, title, amount, exp_type, category, date_str, notes))
    conn.commit()
    conn.close()

    if request.is_json:
        return jsonify({'success': True, 'message': 'Transaction logged'})
    flash('Transaction logged successfully!', 'success')
    return redirect(url_for('expenses'))

@app.route('/api/expenses/<int:exp_id>/delete', methods=['POST'])
@login_required
def delete_expense(exp_id):
    user_id = session['user_id']
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (exp_id, user_id))
    conn.commit()
    conn.close()
    if request.is_json:
        return jsonify({'success': True})
    flash('Transaction removed.', 'info')
    return redirect(url_for('expenses'))

@app.route('/api/expenses/budget', methods=['POST'])
@login_required
def update_budget():
    user_id = session['user_id']
    data = request.get_json() if request.is_json else request.form
    budget = float(data.get('monthly_budget', 2500.0))

    conn = get_db()
    conn.execute("UPDATE users SET monthly_budget = ? WHERE id = ?", (budget, user_id))
    conn.commit()
    conn.close()

    if request.is_json:
        return jsonify({'success': True, 'budget': budget})
    flash('Monthly budget updated!', 'success')
    return redirect(url_for('expenses'))

# ----------------- STUDY PLANNER -----------------

@app.route('/study')
@login_required
def study():
    user_id = session['user_id']
    conn = get_db()
    subjects = conn.execute("""
        SELECT * FROM study_subjects WHERE user_id = ? ORDER BY exam_date ASC
    """, (user_id,)).fetchall()

    sessions = conn.execute("""
        SELECT ss.*, sub.name as subject_name, sub.color as subject_color
        FROM study_sessions ss
        LEFT JOIN study_subjects sub ON ss.subject_id = sub.id
        WHERE ss.user_id = ?
        ORDER BY ss.created_at DESC LIMIT 15
    """, (user_id,)).fetchall()
    conn.close()

    today_d = date.today()
    subject_cards = []
    for s in subjects:
        days_left = None
        if s['exam_date']:
            try:
                ex = datetime.strptime(s['exam_date'], '%Y-%m-%d').date()
                days_left = (ex - today_d).days
            except Exception:
                pass
        subject_cards.append({
            'id': s['id'],
            'name': s['name'],
            'color': s['color'],
            'exam_date': s['exam_date'],
            'target_hours': s['target_hours'],
            'days_left': days_left
        })

    total_minutes = sum(s['duration_minutes'] for s in sessions)

    return render_template(
        'study.html',
        subjects=subject_cards,
        sessions=sessions,
        total_minutes=total_minutes
    )

@app.route('/api/study/subjects', methods=['POST'])
@login_required
def add_subject():
    user_id = session['user_id']
    data = request.get_json() if request.is_json else request.form

    name = data.get('name', '').strip()
    color = data.get('color', '#6366f1')
    exam_date = data.get('exam_date', '')
    target_hours = float(data.get('target_hours', 20.0))

    if not name:
        return jsonify({'error': 'Subject name required'}), 400

    conn = get_db()
    conn.execute("""
        INSERT INTO study_subjects (user_id, name, color, exam_date, target_hours)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, name, color, exam_date, target_hours))
    conn.commit()
    conn.close()

    if request.is_json:
        return jsonify({'success': True})
    flash('Subject added successfully!', 'success')
    return redirect(url_for('study'))

@app.route('/api/study/subjects/<int:sub_id>/delete', methods=['POST'])
@login_required
def delete_subject(sub_id):
    user_id = session['user_id']
    conn = get_db()
    conn.execute("DELETE FROM study_subjects WHERE id = ? AND user_id = ?", (sub_id, user_id))
    conn.commit()
    conn.close()
    if request.is_json:
        return jsonify({'success': True})
    flash('Subject removed.', 'info')
    return redirect(url_for('study'))

@app.route('/api/study/sessions', methods=['POST'])
@login_required
def log_study_session():
    user_id = session['user_id']
    data = request.get_json() or {}

    subject_id = data.get('subject_id')
    duration = int(data.get('duration_minutes', 25))
    notes = data.get('notes', 'Pomodoro session completed')

    conn = get_db()
    conn.execute("""
        INSERT INTO study_sessions (user_id, subject_id, duration_minutes, notes)
        VALUES (?, ?, ?, ?)
    """, (user_id, subject_id, duration, notes))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f'Logged {duration} minutes of focus!'})

# ----------------- HABIT TRACKER -----------------

@app.route('/habits')
@login_required
def habits():
    user_id = session['user_id']
    conn = get_db()
    raw_habits = conn.execute("SELECT * FROM habits WHERE user_id = ?", (user_id,)).fetchall()
    
    today = date.today()
    past_7_days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]

    habit_rows = []
    for h in raw_habits:
        # Fetch completions for past 7 days
        logs = conn.execute("""
            SELECT date, completed FROM habit_logs 
            WHERE habit_id = ? AND date >= ?
        """, (h['id'], past_7_days[0].isoformat())).fetchall()
        log_map = {l['date']: l['completed'] for l in logs}

        day_checks = []
        for d in past_7_days:
            d_str = d.isoformat()
            day_checks.append({
                'date': d_str,
                'completed': bool(log_map.get(d_str, 0) == 1),
                'is_today': (d == today),
                'label': d.strftime('%a')
            })

        # Calculate current streak
        streak = 0
        curr = today
        # If not done today, start from yesterday
        if not log_map.get(today.isoformat(), 0):
            curr = curr - timedelta(days=1)

        while True:
            row = conn.execute("""
                SELECT completed FROM habit_logs WHERE habit_id = ? AND date = ? AND completed = 1
            """, (h['id'], curr.isoformat())).fetchone()
            if row:
                streak += 1
                curr = curr - timedelta(days=1)
            else:
                break

        habit_rows.append({
            'id': h['id'],
            'name': h['name'],
            'category': h['category'],
            'icon': h['icon'],
            'streak': streak,
            'days': day_checks,
            'done_today': bool(log_map.get(today.isoformat(), 0) == 1)
        })

    conn.close()
    return render_template('habits.html', habits=habit_rows, past_days=past_7_days)

@app.route('/api/habits', methods=['POST'])
@login_required
def add_habit():
    user_id = session['user_id']
    data = request.get_json() if request.is_json else request.form

    name = data.get('name', '').strip()
    category = data.get('category', 'Health')
    icon = data.get('icon', 'sparkles')

    if not name:
        return jsonify({'error': 'Habit name is required'}), 400

    conn = get_db()
    conn.execute("""
        INSERT INTO habits (user_id, name, category, icon)
        VALUES (?, ?, ?, ?)
    """, (user_id, name, category, icon))
    conn.commit()
    conn.close()

    if request.is_json:
        return jsonify({'success': True})
    flash('Habit added!', 'success')
    return redirect(url_for('habits'))

@app.route('/api/habits/<int:habit_id>/toggle', methods=['POST'])
@login_required
def toggle_habit(habit_id):
    user_id = session['user_id']
    data = request.get_json() or {}
    target_date = data.get('date', date.today().isoformat())

    conn = get_db()
    cursor = conn.cursor()
    existing = cursor.execute("""
        SELECT id, completed FROM habit_logs 
        WHERE habit_id = ? AND user_id = ? AND date = ?
    """, (habit_id, user_id, target_date)).fetchone()

    new_val = 1
    if existing:
        new_val = 0 if existing['completed'] == 1 else 1
        cursor.execute("UPDATE habit_logs SET completed = ? WHERE id = ?", (new_val, existing['id']))
    else:
        cursor.execute("""
            INSERT INTO habit_logs (habit_id, user_id, date, completed)
            VALUES (?, ?, ?, 1)
        """, (habit_id, user_id, target_date))

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'completed': bool(new_val == 1)})

@app.route('/api/habits/<int:habit_id>/delete', methods=['POST'])
@login_required
def delete_habit(habit_id):
    user_id = session['user_id']
    conn = get_db()
    conn.execute("DELETE FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id))
    conn.commit()
    conn.close()
    if request.is_json:
        return jsonify({'success': True})
    flash('Habit deleted.', 'info')
    return redirect(url_for('habits'))

# ----------------- AI CHATBOT -----------------

@app.route('/chat')
@login_required
def chat():
    user_id = session['user_id']
    conn = get_db()
    messages = conn.execute("""
        SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id ASC
    """, (user_id,)).fetchall()
    conn.close()
    return render_template('chat.html', messages=messages)

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    user_id = session['user_id']
    data = request.get_json() or {}
    message_text = data.get('message', '').strip()

    if not message_text:
        return jsonify({'error': 'Message cannot be empty'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Save user message and commit immediately
    cursor.execute("""
        INSERT INTO chat_messages (user_id, role, content)
        VALUES (?, 'user', ?)
    """, (user_id, message_text))
    conn.commit()
    conn.close()

    # Generate intelligent response
    ai_response = LifeAIEngine.process_chat_message(user_id, message_text)

    # Save assistant response
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_messages (user_id, role, content)
        VALUES (?, 'assistant', ?)
    """, (user_id, ai_response))
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'user_message': message_text,
        'reply': ai_response
    })

@app.route('/api/chat/clear', methods=['POST'])
@login_required
def clear_chat():
    user_id = session['user_id']
    conn = get_db()
    conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ----------------- AI RECOMMENDATIONS -----------------

@app.route('/recommendations')
@login_required
def recommendations():
    user_id = session['user_id']
    ctx = LifeAIEngine.get_user_context(user_id)
    recs = LifeAIEngine.generate_recommendations(user_id)
    return render_template('recommendations.html', ctx=ctx, recommendations=recs)

# ----------------- PROFILE & SETTINGS -----------------

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        budget = float(request.form.get('monthly_budget', 2500.0))
        theme = request.form.get('theme', 'dark')
        new_password = request.form.get('new_password', '').strip()

        if new_password:
            pwd_hash = generate_password_hash(new_password)
            cursor.execute("""
                UPDATE users SET full_name = ?, email = ?, monthly_budget = ?, theme = ?, password_hash = ?
                WHERE id = ?
            """, (full_name, email, budget, theme, pwd_hash, user_id))
        else:
            cursor.execute("""
                UPDATE users SET full_name = ?, email = ?, monthly_budget = ?, theme = ?
                WHERE id = ?
            """, (full_name, email, budget, theme, user_id))

        conn.commit()
        session['theme'] = theme
        flash('Profile settings updated successfully!', 'success')

    user = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/api/reset-data', methods=['POST'])
@login_required
def reset_starter_data():
    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    # Delete current user's data
    cursor.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM study_sessions WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM study_subjects WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM habit_logs WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM habits WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM ai_recommendations WHERE user_id = ?", (user_id,))
    
    # Repopulate
    populate_user_starter_data(user_id, conn)
    conn.commit()
    conn.close()
    flash('Dashboard restored to default sample data!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
