import sqlite3
import os
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'lifeai.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        monthly_budget REAL DEFAULT 2500.0,
        theme TEXT DEFAULT 'dark',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT DEFAULT 'Work',
        priority TEXT DEFAULT 'Medium',
        due_date TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        amount REAL NOT NULL,
        type TEXT DEFAULT 'expense',
        category TEXT DEFAULT 'Other',
        date TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS study_subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        color TEXT DEFAULT '#4f46e5',
        exam_date TEXT,
        target_hours REAL DEFAULT 20.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS study_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject_id INTEGER,
        duration_minutes INTEGER NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES study_subjects (id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'General',
        icon TEXT DEFAULT 'sparkles',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS habit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        completed INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(habit_id, date),
        FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS ai_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        action_url TEXT,
        action_text TEXT,
        is_dismissed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    ''')

    conn.commit()
    conn.close()

def seed_demo_user_if_needed():
    """Seeds a demo user with rich realistic data so user or tester can jump right in!"""
    conn = get_db()
    cursor = conn.cursor()

    demo = cursor.execute("SELECT id FROM users WHERE username = 'demo'").fetchone()
    if not demo:
        # Create demo user
        pwd_hash = generate_password_hash("demo123")
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, monthly_budget, theme)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('demo', 'demo@lifeai.local', pwd_hash, 'Alex Morgan', 3000.0, 'dark'))
        user_id = cursor.lastrowid
        populate_user_starter_data(user_id, conn)

    conn.commit()
    conn.close()

def populate_user_starter_data(user_id, conn=None):
    should_close = False
    if conn is None:
        conn = get_db()
        should_close = True
    cursor = conn.cursor()

    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    tomorrow = today + timedelta(days=1)
    in_three_days = today + timedelta(days=3)
    in_a_week = today + timedelta(days=7)

    # 1. Tasks
    tasks = [
        ("Finalize Machine Learning presentation", "Prepare slides 10-25 and practice speaker notes", "Study", "Urgent", today.isoformat(), "Pending"),
        ("Review monthly cloud hosting bill", "Audit AWS and database instances for cost optimization", "Finance", "High", tomorrow.isoformat(), "Pending"),
        ("30-minute cardio workout", "Interval sprint training at gym or outdoors", "Health", "Medium", today.isoformat(), "Completed"),
        ("Submit algorithms assignment", "Implement Dijkstra and A* pathfinding graph search", "Study", "High", in_three_days.isoformat(), "Pending"),
        ("Grocery run - fresh produce", "Buy apples, spinach, chicken breast, almond milk", "Personal", "Low", in_a_week.isoformat(), "Pending"),
        ("Clean and organize workspace desk", "Cable management and wipe monitors", "Personal", "Low", yesterday.isoformat(), "Completed")
    ]
    cursor.executemany('''
        INSERT INTO tasks (user_id, title, description, category, priority, due_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', [(user_id, t[0], t[1], t[2], t[3], t[4], t[5]) for t in tasks])

    # 2. Expenses
    expenses = [
        ("Monthly Tech Salary", 4200.0, "income", "Salary", today.replace(day=1).isoformat(), "Direct deposit"),
        ("Organic Grocery Store", 112.50, "expense", "Food", yesterday.isoformat(), "Whole Foods weekly restock"),
        ("Coffee & Matcha with Team", 14.80, "expense", "Food", today.isoformat(), "Artisan Roasters"),
        ("Electricity & Fiber Internet", 135.00, "expense", "Utilities", (today - timedelta(days=5)).isoformat(), "Monthly bills"),
        ("Gym & Fitness Pass", 65.00, "expense", "Health", (today - timedelta(days=10)).isoformat(), "Monthly fitness membership"),
        ("Machine Learning Textbook", 54.00, "expense", "Education", (today - timedelta(days=12)).isoformat(), "Pattern Recognition reference book"),
        ("Metro Transit Card", 45.00, "expense", "Transport", (today - timedelta(days=8)).isoformat(), "Monthly transit recharge")
    ]
    cursor.executemany('''
        INSERT INTO expenses (user_id, title, amount, type, category, date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', [(user_id, e[0], e[1], e[2], e[3], e[4], e[5]) for e in expenses])

    # 3. Study Subjects & Sessions
    subjects = [
        ("Artificial Intelligence & ML", "#6366f1", (today + timedelta(days=14)).isoformat(), 35.0),
        ("Algorithms & Data Structures", "#06b6d4", (today + timedelta(days=21)).isoformat(), 25.0),
        ("System Design & Architecture", "#10b981", (today + timedelta(days=35)).isoformat(), 20.0),
        ("Cybersecurity Fundamentals", "#f59e0b", (today + timedelta(days=45)).isoformat(), 15.0)
    ]
    subject_ids = []
    for s in subjects:
        cursor.execute('''
            INSERT INTO study_subjects (user_id, name, color, exam_date, target_hours)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, s[0], s[1], s[2], s[3]))
        subject_ids.append(cursor.lastrowid)

    # Study Sessions
    if subject_ids:
        sessions = [
            (subject_ids[0], 50, "Covered Convolutional Neural Networks and backprop"),
            (subject_ids[0], 25, "Reviewed transformer attention mechanisms"),
            (subject_ids[1], 45, "Graph traversal and shortest path problem sets"),
            (subject_ids[2], 30, "Read caching patterns and database sharding principles")
        ]
        cursor.executemany('''
            INSERT INTO study_sessions (user_id, subject_id, duration_minutes, notes)
            VALUES (?, ?, ?, ?)
        ''', [(user_id, sess[0], sess[1], sess[2]) for sess in sessions])

    # 4. Habits & Habit Logs
    habits = [
        ("Morning Meditation (10m)", "Health", "brain"),
        ("Drink 2.5L Water", "Health", "droplet"),
        ("Read 20 Pages Non-fiction", "Study", "book-open"),
        ("Code / LeetCode 1 Problem", "Study", "code"),
        ("Limit Screen Time after 10PM", "Personal", "moon")
    ]
    habit_ids = []
    for h in habits:
        cursor.execute('''
            INSERT INTO habits (user_id, name, category, icon)
            VALUES (?, ?, ?, ?)
        ''', (user_id, h[0], h[1], h[2]))
        habit_ids.append(cursor.lastrowid)

    # Habit Logs for the last 7 days to simulate active streaks
    for idx, h_id in enumerate(habit_ids):
        # Give varying consistency
        days_to_complete = 7 if idx == 0 else (6 if idx == 1 else 5)
        for d in range(days_to_complete):
            log_date = (today - timedelta(days=d)).isoformat()
            cursor.execute('''
                INSERT OR IGNORE INTO habit_logs (habit_id, user_id, date, completed)
                VALUES (?, ?, ?, 1)
            ''', (h_id, user_id, log_date))

    # 5. AI Chat Messages
    initial_chat = [
        ("assistant", "Hello Alex! I am your LifeAI assistant. I am actively monitoring your tasks, study schedule, budget, and habits. How can I help you thrive today?"),
        ("user", "What should I focus on this afternoon?"),
        ("assistant", "Based on your current plan, your top priority is the **Machine Learning presentation** due today! I recommend doing a 25-minute Pomodoro focus block right now, followed by a quick water break. You're also on a 7-day streak for Morning Meditation—awesome momentum!")
    ]
    cursor.executemany('''
        INSERT INTO chat_messages (user_id, role, content)
        VALUES (?, ?, ?)
    ''', [(user_id, c[0], c[1]) for c in initial_chat])

    # 6. AI Recommendations
    recs = [
        ("tasks", "Urgent Task Deadline Ahead", "Your 'Machine Learning presentation' is due today. Allocate a dedicated 50-minute study session to finish it before dinner.", "/study", "Start Focus Session"),
        ("finance", "Budget on Track!", "You've only utilized 14% of your $3,000 monthly limit. Current projected savings this month is $3,773.70.", "/expenses", "View Budget Breakdown"),
        ("habits", "7-Day Streak Milestone Reached", "You reached a 7-day streak in Morning Meditation! Keep the momentum alive tomorrow morning.", "/habits", "Check Habit Heatmap"),
        ("study", "Upcoming Exam Alert: AI & ML", "Your Artificial Intelligence exam is in 14 days. You have completed 1.25 of your 35 target hours.", "/study", "Plan Study Schedule")
    ]
    cursor.executemany('''
        INSERT INTO ai_recommendations (user_id, category, title, description, action_url, action_text)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', [(user_id, r[0], r[1], r[2], r[3], r[4]) for r in recs])

    if should_close:
        conn.commit()
        conn.close()
