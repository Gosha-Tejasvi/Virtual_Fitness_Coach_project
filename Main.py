
from fastapi import FastAPI, Request, Form, WebSocket, Depends, Body
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import sqlite3
import uvicorn
from database import init_db, save_performance_data
from auth import hash_password, verify_password
from pose_utils import generate_frames, get_feedback, stop_session  # <- Added stop_session
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="secret")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
# Initialize database
init_db()
# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
@app.get("/signup")
async def signup_get(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
):
    hashed_pw = hash_password(password)
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, age, gender) VALUES (?, ?, ?, ?)",
                  (username, hashed_pw, age, gender))
        conn.commit()
        conn.close()
        return RedirectResponse(url="/login", status_code=302)
    except sqlite3.IntegrityError:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Username already exists"})
@app.get("/login")
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()

    if user and verify_password(password, user[2]):
        request.session["user"] = {"id": user[0], "username": user[1]}
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''SELECT exercise_name, repetitions, hold_time, date FROM user_performance WHERE user_id = ? ORDER BY date DESC''', (user["id"],))
    performance_data = c.fetchall()
    conn.close()
    exercises = ["Squat", "Pushup", "Plank", "Warrior", "ArmRaise", "SideStretch"]
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "exercises": exercises,
        "performance_data": performance_data
    })
@app.get("/pose")
async def pose_page(request: Request, exercise: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("pose.html", {
        "request": request,
        "exercise": exercise,
        "user": user
    })
@app.get("/video_feed")
def video_feed(request: Request, exercise: str):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    username = user["username"]
    return StreamingResponse(generate_frames(exercise, username), media_type="multipart/x-mixed-replace; boundary=frame")
@app.get("/get_feedback")
def get_feedback_api(request: Request, exercise: str):
    user = request.session.get("user")
    if not user:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    username = user["username"]
    feedback = get_feedback(exercise, username)
    return JSONResponse(content={"feedback": feedback})
@app.get("/stop_session")  # <- NEW endpoint
def stop_session_route(request: Request, exercise: str):
    user = request.session.get("user")
    if not user:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    stop_session()  # Stop session and save performance data
    return JSONResponse(content={"message": "Session stopped and performance data saved."})

@app.get("/performance_data")
async def get_performance_data(request: Request):
    user = request.session.get("user")
    if not user:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        SELECT date, SUM(repetitions) as total_reps, SUM(hold_time) as total_hold
        FROM user_performance
        WHERE user_id = ?
        GROUP BY date
        ORDER BY date ASC
    """, (user["id"],))
    data = c.fetchall()
    conn.close()
    dates = [row[0] for row in data]
    reps = [row[1] for row in data]
    hold_times = [round(row[2], 1) if row[2] else 0 for row in data]
    return JSONResponse(content={"dates": dates, "reps": reps, "hold_times": hold_times})
@app.post("/submit_performance")
async def submit_performance(
    request: Request,
    exercise: str = Form(...),
    repetitions: int = Form(...),
    hold_time: float = Form(...),
):
    user = request.session.get("user")
    if not user:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    username = user["username"]
    print(f"[DEBUG] Saving data for: {username}, {exercise}, Reps: {repetitions}, Hold: {hold_time}")
    save_performance_data(username, exercise, repetitions, hold_time)
    return JSONResponse(content={"message": "Performance saved"})
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)













