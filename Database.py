import sqlite3
from datetime import datetime
DB_NAME = "users.db"
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            age INTEGER,
            gender TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            repetitions INTEGER DEFAULT 0,
            hold_time REAL DEFAULT 0.0,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()
def save_performance_data(username, exercise_name, repetitions, hold_time):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Get the user_id for the username
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    result = c.fetchone()
    if result:
        user_id = result[0]
        # Insert performance data
        c.execute("""
            INSERT INTO user_performance (user_id, exercise_name, repetitions, hold_time, date)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (user_id, exercise_name, repetitions, hold_time))
        conn.commit()
    else:
        print(f"[Error] Username {username} not found in users table.")
    conn.close()
