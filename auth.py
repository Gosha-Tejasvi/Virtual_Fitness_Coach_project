from passlib.context import CryptContext
import sqlite3
# Create password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# --- Helper Functions ---
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
def create_user(username: str, password: str, age: int, gender: str) -> bool:
    hashed_pw = hash_password(password)
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, age, gender) VALUES (?, ?, ?, ?)",
                  (username, hashed_pw, age, gender))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
def authenticate_user(username: str, password: str):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    if user and verify_password(password, user[2]):
        return {
            "id": user[0],
            "username": user[1]
        }
    return None
