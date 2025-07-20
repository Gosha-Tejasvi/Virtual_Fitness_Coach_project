# pose_utils.py
import cv2
import mediapipe as mp
import pyttsx3
import time
import numpy as np
import threading
import os
from database import save_performance_data
# MediaPipe Setup
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
# Pyttsx3 Setup
engine = pyttsx3.init()
# Global State
last_feedback_time = 0
hold_start_time = None
prev_feedback = ""
rep_count = 0
hold_time = 0
current_feedback = "Keep going"
pushup_down = False
squat_down = False
session_active = True  # NEW: Flag to control stopping
def reset_globals():
    global last_feedback_time, hold_start_time, prev_feedback, rep_count, hold_time, current_feedback, pushup_down, squat_down
    last_feedback_time = 0
    hold_start_time = None
    prev_feedback = ""
    rep_count = 0
    hold_time = 0
    current_feedback = "Keep going"
    pushup_down = False
    squat_down = False
def stop_session():
    global session_active
    session_active = False  # Trigger stopping in generate_frames()
def speak_feedback(text):
    global last_feedback_time, prev_feedback
    current_time = time.time()
    if text != prev_feedback and (current_time - last_feedback_time > 1.0):
        threading.Thread(target=_speak, args=(text,)).start()
        last_feedback_time = current_time
        prev_feedback = text
def _speak(text):
    print(f"Speaking: {text}")
    engine.say(text)
    engine.runAndWait()
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = abs(radians * 180.0 / np.pi)
    return angle if angle <= 180 else 360 - angle
def analyze_pose(landmarks, exercise):
    global hold_start_time, rep_count, hold_time, pushup_down, squat_down, current_feedback
    feedback = "Keep going"
    is_correct = False
    current_time = time.time()
    try:
        # Landmark extraction
        left_shoulder = (landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x,
                         landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y)
        left_elbow = (landmarks[mp_pose.PoseLandmark.LEFT_ELBOW].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_ELBOW].y)
        left_wrist = (landmarks[mp_pose.PoseLandmark.LEFT_WRIST].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_WRIST].y)
        left_hip = (landmarks[mp_pose.PoseLandmark.LEFT_HIP].x,
                    landmarks[mp_pose.PoseLandmark.LEFT_HIP].y)
        left_knee = (landmarks[mp_pose.PoseLandmark.LEFT_KNEE].x,
                     landmarks[mp_pose.PoseLandmark.LEFT_KNEE].y)
        left_ankle = (landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].y)
        # Exercise logic
        if exercise == "Squat":
            angle = calculate_angle(left_hip, left_knee, left_ankle)
            if angle < 100:
                squat_down = True
            elif angle > 140 and squat_down:
                squat_down = False
                rep_count += 1
                speak_feedback("Good squat! Keep going!")
            is_correct = 90 <= angle <= 130
            feedback = "Good squat!" if is_correct else "Go deeper!"
        elif exercise == "Pushup":
            angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
            if angle < 80:
                pushup_down = True
            elif angle > 120 and pushup_down:
                pushup_down = False
                rep_count += 1
                speak_feedback("Good pushup! Keep going!")
            is_correct = 70 <= angle <= 110
            feedback = "Good pushup!" if is_correct else "Bend arms more!"
        elif exercise == "Plank":
            angle = calculate_angle(left_shoulder, left_hip, left_knee)
            is_correct = 160 <= angle <= 180
            feedback = "Great plank!" if is_correct else "Keep your back straight"
        elif exercise == "ArmRaise":
            angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
            is_correct = 160 <= angle <= 180
            feedback = "Great arm raise!" if is_correct else "Raise your arms fully!"
        elif exercise == "Warrior":
            angle = calculate_angle(left_hip, left_knee, left_ankle)
            is_correct = 120 <= angle <= 150
            feedback = "Good warrior pose!" if is_correct else "Adjust your stance!"
        elif exercise == "SideStretch":
            angle = calculate_angle(left_hip, left_shoulder, left_elbow)
            is_correct = 100 <= angle <= 140
            feedback = "Nice stretch!" if is_correct else "Lean more!"

        # Hold time logic
        if exercise in ["Plank", "ArmRaise", "Warrior", "SideStretch"]:
            if is_correct:
                if hold_start_time is None:
                    hold_start_time = current_time
                hold_time = current_time - hold_start_time
                if hold_time >= 1.0:
                    speak_feedback("Good hold! Keep going!")
            else:
                hold_start_time = None
                hold_time = 0
    except Exception as e:
        print(f"[POSE ERROR] {e}")
        feedback = "Landmarks not detected"
        is_correct = False
    current_feedback = feedback
    return feedback, is_correct, rep_count, hold_time
def generate_frames(exercise, username):
    global session_active
    session_active = True
    reset_globals()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
    try:
        while session_active:
            success, frame = cap.read()
            if not success:
                print("Error: Failed to capture frame.")
                break
            frame = cv2.flip(frame, 1)
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                feedback, _, reps, hold = analyze_pose(results.pose_landmarks.landmark, exercise)
                cv2.putText(frame, feedback, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Reps: {reps}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                cv2.putText(frame, f"Hold: {hold:.1f}s", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                print("Error: Failed to encode frame.")
                break
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Current Working Directory:", os.getcwd())
        print(f"[Saving Data] User: {username}, Exercise: {exercise}, Reps: {rep_count}, Hold Time: {hold_time:.2f}")
        save_performance_data(username, exercise, rep_count, hold_time)
        engine.stop()
def get_feedback(exercise, username):
    return {
        "feedback": current_feedback,
        "repetitions": rep_count,
        "hold_time": round(hold_time, 1)
    }
