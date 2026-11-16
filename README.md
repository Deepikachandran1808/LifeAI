# 🌟 LifeAI - AI-Powered Daily Life Assistant

LifeAI is an autonomous, intelligent personal operating system designed to manage your daily life across productivity, finances, habits, study plans, and interactive AI coaching. Built with **HTML5, CSS3, JavaScript, Python Flask, and SQLite**.

---

## 🚀 Features Overview

1. **🤖 Live AI Chatbot Assistant**
   - Natural language conversational life coach.
   - Context-aware: aware of your actual pending tasks, monthly expenses, active habit streaks, and exam schedules.
   - Natural language command execution:
     - `add task Finish report tomorrow urgent`
     - `add expense $24 lunch`
     - `completed habit meditation`
     - `What should I focus on today?`
     - `How is my budget looking this month?`
   - Prompt suggestion chips, formatted responses, and persistent chat history.

2. **✅ Feature-Packed Task Manager**
   - Categorize by Work, Study, Health, Finance, and Personal.
   - Priority tagging: `Urgent`, `High`, `Medium`, and `Low`.
   - Due date tracking with countdowns.
   - Filter by status (Pending / Completed) and priority.
   - **AI Task Decomposition**: Dissects complex assignments into bite-sized actionable sprints.

3. **💳 Expense & Budget Tracker**
   - Monthly budget limit setting with dynamic progress bar and threshold alerts.
   - Visual spending breakdown using interactive **Chart.js** donut charts.
   - Log income and expenses with category tagging and notes.
   - Real-time calculation of net savings and monthly burn rates.

4. **📚 Study Planner & Pomodoro Focus Hub**
   - Course and subject tracking with target study hours and exam countdown badges.
   - **Interactive Pomodoro Timer**:
     - Focus (25m), Short Break (5m), and Long Break (15m).
     - Synthesized audio chimes powered by the **Web Audio API**.
     - Auto-logs completed study minutes directly into your database.
   - Study history log with subject attribution.

5. **🌱 Atomic Habit Tracker**
   - Interactive 7-day visual check-in matrix.
   - Automatic consecutive day streak counter (`🔥 7d streak`).
   - Motivational milestone badges (3-Day Spark, 7-Day Momentum, 21-Day Habit Master).
   - Instant toggle for today or past days.

6. **💡 Personalized AI Recommendations**
   - Multi-metric daily life audit calculating a **0-100 LifeAI Productivity Score**.
   - Identifies at-risk habit streaks, urgent deadlines, and budget spikes.
   - One-click actionable interventions with direct navigation.

7. **🛡️ Secure Authentication & Data Privacy**
   - PBKDF2 cryptographic password hashing via Werkzeug.
   - Session-based access control with `@login_required`.
   - Local SQLite database stored securely on your machine.
   - Pre-populated starter data option for instant evaluation.

8. **🎨 Modern Responsive UI**
   - Neo-minimalist glassmorphism styling with dark/light theme switching.
   - Mobile-responsive collapsible sidebar.
   - Clean SVG icons and custom CSS design system.

---

## 🛠️ Quick Start Guide

### 1. Run LifeAI
```bash
# Navigate to the project directory
cd "C:\Users\Deepika Gowda\.gemini\antigravity\scratch\lifeai"

# Run the Flask app with the included virtual environment
.venv\Scripts\python.exe app.py
```

### 2. Access the Web Dashboard
Open your browser and navigate to:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

### 3. Login
- **Demo User:**
  - Username: `demo`
  - Password: `demo123`
- Or click **"Create an Account"** to register your own custom user!
