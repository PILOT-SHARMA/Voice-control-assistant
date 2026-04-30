"""
Flask Web Server — Real-Time AI Voice Assistant for Blind Users
================================================================
Provides web API endpoints for the voice assistant, camera feed,
mode switching, and scene description.

Routes:
  /                     → Main UI
  /api/chat             → Process voice/text commands
  /api/mode             → Get/set current mode
  /api/describe         → One-shot scene description
  /api/video_feed       → Live MJPEG camera stream
  /api/status           → System status
  /api/analyze-image    → Gemini-based image analysis (legacy)
  /api/history          → Chat history CRUD

Author : Arpit
"""

from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import json
import os
import threading
import cv2
import time

from dotenv import load_dotenv
load_dotenv()

# Optional: Gemini for advanced image analysis
try:
    import google.generativeai as genai
    import PIL.Image
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from assistant import process_command_web, speak, mode_manager

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

HISTORY_FILE = "chat_history.json"
history_lock = threading.Lock()


# ──────────────────────────────────────────────
# MAIN PAGE
# ──────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


# ──────────────────────────────────────────────
# CHAT / COMMAND API
# ──────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    command = data.get("message", "").lower().strip()
    if not command:
        return jsonify({"error": "No message provided"}), 400

    result = process_command_web(command)
    response_text = result.get("response", "")

    # Speak the response via TTS (skip if action is 'ignore')
    if response_text and result.get("action") != "ignore":
        speak(response_text)

    # Include current mode in response
    result["mode"] = mode_manager.mode

    return jsonify(result)


# ──────────────────────────────────────────────
# MODE API
# ──────────────────────────────────────────────
@app.route("/api/mode", methods=["GET"])
def get_mode():
    vs = mode_manager._vision_system
    return jsonify({
        "mode": mode_manager.mode,
        "camera_running": vs.is_running if vs else False,
    })


@app.route("/api/mode", methods=["POST"])
def set_mode():
    data = request.json
    new_mode = data.get("mode", "").lower().strip()

    if new_mode == "vision":
        mode_manager.switch_to_vision()
    elif new_mode == "navigation":
        mode_manager.switch_to_navigation()
    elif new_mode == "normal":
        mode_manager.switch_to_normal()
    else:
        return jsonify({"error": f"Unknown mode: {new_mode}"}), 400

    return jsonify({
        "mode": mode_manager.mode,
        "message": f"Switched to {new_mode} mode.",
    })


# ──────────────────────────────────────────────
# ONE-SHOT SCENE DESCRIPTION
# ──────────────────────────────────────────────
@app.route("/api/describe", methods=["POST"])
def describe_scene():
    vs = mode_manager._vision_system
    if vs is None:
        return jsonify({"error": "Vision system not available"}), 500

    description = vs.describe_scene()
    speak(description)
    return jsonify({"description": description})


# ──────────────────────────────────────────────
# LIVE VIDEO FEED (MJPEG)
# ──────────────────────────────────────────────
def _generate_frames():
    """Generator: yields MJPEG frames from the vision system."""
    vs = mode_manager._vision_system
    while True:
        if vs and vs.is_running:
            frame = vs.get_latest_frame()
            if frame is not None:
                # Resize for web display
                h, w = frame.shape[:2]
                scale = min(640 / w, 480 / h)
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' +
                           buffer.tobytes() + b'\r\n')
        time.sleep(0.1)


@app.route("/api/video_feed")
def video_feed():
    return Response(
        _generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


# ──────────────────────────────────────────────
# SYSTEM STATUS
# ──────────────────────────────────────────────
@app.route("/api/status", methods=["GET"])
def status():
    vs = mode_manager._vision_system
    return jsonify({
        "mode": mode_manager.mode,
        "camera_running": vs.is_running if vs else False,
        "vision_available": vs is not None,
        "gemini_available": GEMINI_AVAILABLE,
    })


@app.route("/api/detections", methods=["GET"])
def get_detections():
    """Return recent detection log entries for the UI."""
    vs = mode_manager._vision_system
    if vs is None:
        return jsonify({"log": [], "detections": []})
    log = vs.get_detection_log(20)
    current = vs.get_latest_detections()
    # Serialize detections (remove non-JSON-safe fields)
    safe_current = []
    for d in current:
        safe_current.append({
            "class": d["class"],
            "zone": d["zone"],
            "distance": d["distance"],
            "confidence": round(d["confidence"], 2),
            "area_ratio": round(d.get("area_ratio", 0), 4),
        })
    return jsonify({"log": log, "detections": safe_current})


# ──────────────────────────────────────────────
# GEMINI IMAGE ANALYSIS (legacy endpoint)
# ──────────────────────────────────────────────
@app.route("/api/analyze-image", methods=["POST"])
def analyze_image():
    if not GEMINI_AVAILABLE:
        return jsonify({"error": "Gemini API not configured"}), 500

    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No image selected"}), 400

    try:
        img = PIL.Image.open(file.stream)
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = """You are an AI assistant for blind users.
Describe the image for navigation:
1. Most important object directly ahead
2. Distance (close, 1 meter, far)
3. Direction (left, right, center)
4. Highlight obstacles or dangers
5. Keep sentences short and clear
Example: "There is a chair about one meter ahead, slightly to your right."
If nothing important: "The path ahead appears clear."
Now analyze the image."""

        response = model.generate_content([prompt, img])
        description = response.text.strip()

        if description:
            speak(description)

        return jsonify({"response": description, "action": "speak"})

    except Exception as e:
        print(f"Image analysis error: {e}")
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# CHAT HISTORY
# ──────────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
def get_history():
    if not os.path.exists(HISTORY_FILE):
        return jsonify([])
    with history_lock:
        try:
            with open(HISTORY_FILE, "r") as f:
                return jsonify(json.load(f))
        except Exception:
            return jsonify([])


@app.route("/api/history", methods=["POST"])
def save_history():
    data = request.json
    with history_lock:
        try:
            history = []
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r") as f:
                    try:
                        history = json.load(f)
                    except json.JSONDecodeError:
                        history = []

            session_id = data.get("id")
            found = False
            for i, s in enumerate(history):
                if s.get("id") == session_id:
                    history[i] = data
                    found = True
                    break
            if not found:
                history.append(data)

            history.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/history/<session_id>", methods=["DELETE"])
def delete_history(session_id):
    with history_lock:
        try:
            if not os.path.exists(HISTORY_FILE):
                return jsonify({"status": "success"})
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
            history = [s for s in history if s.get("id") != session_id]
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# DIRECT RUN (prefer main.py instead)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    # If run directly, initialize vision system here
    from camera import VisionSystem
    vision = VisionSystem(speak_callback=speak)
    mode_manager.set_vision_system(vision)

    print("=" * 55)
    print("   👁️  VOICE ASSISTANT WEB SERVER  👁️")
    print("   Access UI at: http://localhost:5001")
    print("=" * 55)
    app.run(debug=False, port=5001, use_reloader=False, threaded=True)
