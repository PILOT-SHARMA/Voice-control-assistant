from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
import threading
import queue

import assistant
from assistant import process_command_web

app = Flask(__name__)
CORS(app)

HISTORY_FILE = "chat_history.json"
history_lock = threading.Lock()

# ──────────────────────────────────────────────
# BACKGROUND TTS WORKER (Prevents macOS crashes)
# ──────────────────────────────────────────────
tts_queue = queue.Queue()

def tts_worker():
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate', 170)
    engine.setProperty('volume', 0.9)
    voices = engine.getProperty('voices')
    if len(voices) > 1:
        engine.setProperty('voice', voices[1].id)
    else:
        engine.setProperty('voice', voices[0].id)
        
    while True:
        text = tts_queue.get()
        if text is None:
            break
        print(f"🤖 Assistant (Server TTS): {text}")
        engine.say(text)
        engine.runAndWait()
        tts_queue.task_done()

threading.Thread(target=tts_worker, daemon=True).start()

# ──────────────────────────────────────────────
# FLASK ROUTES
# ──────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    command = data.get("message", "").lower()
    if not command:
        return jsonify({"error": "No message provided"}), 400
    
    # Process the command logic without blocking to speak
    result = process_command_web(command)
    response_text = result.get("response", "")
    
    # Send text to background TTS worker
    if response_text:
        tts_queue.put(response_text)
        
    return jsonify(result)

@app.route("/api/history", methods=["GET"])
def get_history():
    if not os.path.exists(HISTORY_FILE):
        return jsonify([])
    with history_lock:
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
            return jsonify(history)
        except Exception as e:
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
            
            # check if session exists
            session_id = data.get("id")
            existing = False
            for i, session in enumerate(history):
                if session.get("id") == session_id:
                    history[i] = data
                    existing = True
                    break
            if not existing:
                history.append(data)
                
            # sort most recent first
            history.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=4)
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
                json.dump(history, f, indent=4)
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/api/toggle-wake-word", methods=["POST"])
def toggle_wake_word():
    # Toggle global variable in assistant.py
    assistant.USE_WAKE_WORD = not getattr(assistant, "USE_WAKE_WORD", False)
    status = "enabled" if assistant.USE_WAKE_WORD else "disabled"
    return jsonify({"status": "success", "message": f"Wake word {status}"})

if __name__ == "__main__":
    print("=" * 55)
    print("   🌐 VOICE ASSISTANT FLASK SERVER RUNNING 🌐")
    print("   Access the UI at: http://localhost:5000")
    print("=" * 55)
    app.run(debug=True, port=5000, use_reloader=False)
