"""
Voice Assistant — Command Processing & Voice I/O
"""

import speech_recognition as sr
import datetime
import webbrowser
import os
import sys
import subprocess
import time
import re
import threading
import queue

# ──────────────────────────────────────────────
# TTS ENGINE
# ──────────────────────────────────────────────
_tts_queue = queue.Queue()
_tts_last = {"text": None, "t": 0}
_tts_dedup_lock = threading.Lock()

def _tts_worker():
    while True:
        text = _tts_queue.get()
        if text is None:
            break
        try:
            clean = text.replace('"', '').replace("'", "")
            if sys.platform == "darwin":
                subprocess.run(['say', '-v', 'Daniel', '-r', '185', clean],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
        except Exception:
            pass
        finally:
            _tts_queue.task_done()

_tts_thread = threading.Thread(target=_tts_worker, daemon=True)
_tts_thread.start()

def speak(text):
    """Queue text for TTS — dedup identical phrases within 3 seconds."""
    with _tts_dedup_lock:
        now = time.time()
        if _tts_last["text"] == text and now - _tts_last["t"] < 3.0:
            print(f"🔇 Skipped duplicate: {text}")
            return
        _tts_last["text"] = text
        _tts_last["t"] = now
    print(f"🔊 {text}")
    _tts_queue.put(text)

def speak_sync(text):
    speak(text)
    _tts_queue.join()


# ──────────────────────────────────────────────
# SPEECH RECOGNITION
# ──────────────────────────────────────────────
def listen(timeout=5, phrase_limit=6):
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.0
    try:
        with sr.Microphone() as source:
            print("\n🎤 Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.6)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
    except sr.WaitTimeoutError:
        return None
    except OSError:
        return None

    try:
        response = recognizer.recognize_google(audio, language='en-in', show_all=True)
        if not response or not isinstance(response, dict) or 'alternative' not in response:
            return None
        best = response['alternative'][0]
        raw = best['transcript']
        conf = best.get('confidence', 1.0)
        if conf < 0.55:
            return None
        print(f"🗣  Heard: '{raw}' (conf:{conf:.2f})")
        return re.sub(r'\s+', ' ', raw.lower().strip())
    except (sr.UnknownValueError, sr.RequestError):
        return None


# ──────────────────────────────────────────────
# APP / WEBSITE MAPS
# ──────────────────────────────────────────────
APP_MAP = {
    "chrome":    {"darwin": "open -a 'Google Chrome'"},
    "safari":    {"darwin": "open -a Safari"},
    "whatsapp":  {"darwin": "open -a WhatsApp"},
    "telegram":  {"darwin": "open -a Telegram"},
    "vs code":   {"darwin": "open -a 'Visual Studio Code'"},
    "vscode":    {"darwin": "open -a 'Visual Studio Code'"},
    "spotify":   {"darwin": "open -a Spotify"},
    "terminal":  {"darwin": "open -a Terminal"},
    "settings":  {"darwin": "open -a 'System Settings'"},
    "calculator":{"darwin": "open -a Calculator"},
    "notes":     {"darwin": "open -a Notes"},
    "finder":    {"darwin": "open -a Finder"},
    "photos":    {"darwin": "open -a Photos"},
    "music":     {"darwin": "open -a Music"},
    "maps":      {"darwin": "open -a Maps"},
    "messages":  {"darwin": "open -a Messages"},
}

WEBSITE_MAP = {
    "youtube":        "https://www.youtube.com",
    "google":         "https://www.google.com",
    "gmail":          "https://mail.google.com",
    "github":         "https://github.com",
    "wikipedia":      "https://www.wikipedia.org",
    "chatgpt":        "https://chat.openai.com",
    "stack overflow": "https://stackoverflow.com",
    "amazon":         "https://www.amazon.in",
    "twitter":        "https://twitter.com",
    "instagram":      "https://www.instagram.com",
    "facebook":       "https://www.facebook.com",
    "linkedin":       "https://www.linkedin.com",
    "netflix":        "https://www.netflix.com",
    "reddit":         "https://www.reddit.com",
}

_last_open = {"key": None, "t": 0}

def _try_open_app(command):
    for name, cmds in APP_MAP.items():
        if name in command:
            cmd = cmds.get(sys.platform)
            if cmd:
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Opening {name.title()}"
    return None

def _try_open_website(command):
    for site, url in WEBSITE_MAP.items():
        if site in command:
            now = time.time()
            if _last_open["key"] == site and now - _last_open["t"] < 5:
                return f"Opening {site.title()}"
            _last_open["key"] = site
            _last_open["t"] = now
            webbrowser.open(url)
            return f"Opening {site.title()}"
    return None


# ──────────────────────────────────────────────
# MODE MANAGER
# ──────────────────────────────────────────────
class ModeManager:
    def __init__(self):
        self._vision_system = None

    def set_vision_system(self, vs):
        self._vision_system = vs

    @property
    def mode(self):
        # Always "active" — camera always on
        return "active"

mode_manager = ModeManager()


# ──────────────────────────────────────────────
# COMMAND ROUTING — STRICT
# ──────────────────────────────────────────────
def _route(command):
    """Returns response string or None if silent."""
    vs = mode_manager._vision_system

    # ── VISION QUERIES ──
    if any(p in command for p in ["what is in my hand", "what am i holding", "what's in my hand"]):
        return vs.query_hand() if vs else "Camera not ready"

    if any(p in command for p in ["what is in front of me", "what's in front of me", "what can you see"]):
        return vs.query_front() if vs else "Camera not ready"

    if any(p in command for p in ["what is the person holding", "what is the man holding", "what is the woman holding"]):
        return vs.query_person_holding() if vs else "Camera not ready"

    if any(p in command for p in ["can i move forward", "is the path clear", "is path clear"]):
        return vs.query_path() if vs else "Camera not ready"

    # ── OPEN APP / WEBSITE ──
    if "open" in command:
        result = _try_open_app(command)
        if result:
            return result
        result = _try_open_website(command)
        if result:
            return result
        target = command.replace("open", "").strip()
        if target:
            webbrowser.open(f"https://www.google.com/search?q={target}")
            return f"Searching for {target}"
        return None

    # ── TIME / DATE ──
    if "time" in command:
        return f"It is {datetime.datetime.now().strftime('%I:%M %p')}"
    if any(w in command for w in ["date", "today", "what day"]):
        return f"Today is {datetime.datetime.now().strftime('%A, %B %d')}"

    return None  # Silent for unrecognised commands


def process_command(command):
    """Terminal mode command processor."""
    response = _route(command)
    if response:
        speak(response)
    return True  # Keep running


def process_command_web(command):
    """Web API command processor."""
    response = _route(command)
    if response:
        return {"response": response, "action": "speak"}
    return {"response": "", "action": "ignore"}


# ──────────────────────────────────────────────
# MAIN LOOP (terminal mode)
# ──────────────────────────────────────────────
def main_loop():
    speak("Hello, welcome")
    last_cmd, last_t = None, 0
    while True:
        try:
            command = listen()
            if not command:
                continue
            now = time.time()
            if command == last_cmd and now - last_t < 3.0:
                continue
            last_cmd, last_t = command, now
            process_command(command)
        except KeyboardInterrupt:
            break
        except Exception:
            continue
