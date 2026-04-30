# 👁️ VisionGuide — Real-Time AI Voice Assistant for Blind Users

> A fully voice-controlled, computer-vision-powered assistant designed to help visually impaired users navigate their surroundings hands-free.

---

## 🎯 What It Does

VisionGuide uses your **live webcam**, **YOLOv8 object detection**, and **MediaPipe hand tracking** to understand the world around you — then answers your voice commands in real time with short, direct spoken responses.

No wearable required. Just open the browser and speak.

---

## 🗣️ Voice Commands

| Command | Response |
|---|---|
| `"What is in my hand?"` | *"You are holding a bottle"* |
| `"What is in front of me?"` | *"Chair in front of you"* |
| `"What is the person holding?"` | *"The person in front is holding a phone"* |
| `"Can I move forward?"` | *"Yes, path is clear"* or *"No, obstacle ahead"* |
| `"Open YouTube"` | Opens YouTube in browser |
| `"Open Chrome"` | Opens Chrome app |
| `"What time is it?"` | *"It is 09:30 PM"* |

---

## 🧠 Tech Stack

| Layer | Technology |
|---|---|
| Object Detection | [YOLOv8n](https://github.com/ultralytics/ultralytics) |
| Hand Tracking | [MediaPipe HandLandmarker (Tasks API)](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker) |
| Backend | Python · Flask |
| Speech Recognition | Web Speech API (browser) |
| Text-to-Speech | macOS `say` (Daniel voice) / pyttsx3 |
| UI | Vanilla HTML · CSS · JS (Dark glassmorphism) |

---

## ⚡ Features

- 📷 **Camera always ON** — starts automatically when app loads
- 🤚 **Hand-object overlap detection** — knows what you're holding
- 🧭 **3-zone navigation** — LEFT / CENTER / RIGHT with real-time indicators
- 🎙️ **Continuous voice recognition** — auto-restarts after each phrase
- 🔇 **Strict command-only responses** — never speaks unless asked
- 📋 **Live detection log** — scrollable timestamped feed
- 🌐 **Open any app or website** by voice

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/PILOT-SHARMA/Voice-control-assistant.git
cd Voice-control-assistant
```

### 2. Create virtual environment & install dependencies
```bash
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
pip install -r requirements.txt
```

### 3. Download model files
```bash
# YOLOv8 nano — auto-downloads on first run

# MediaPipe Hand Landmarker
curl -L https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task \
     -o hand_landmarker.task
```

### 4. Set up environment (optional — for Gemini image analysis)
```bash
cp .env.example .env
# Add your GEMINI_API_KEY inside .env
```

### 5. Run
```bash
python main.py
```

Open **http://localhost:5001** in **Chrome**.

---

## 📁 Project Structure

```
Voice-control-assistant/
├── main.py              # Entry point (web or terminal mode)
├── app.py               # Flask API server
├── assistant.py         # Voice I/O + command routing
├── camera.py            # YOLOv8 + MediaPipe vision engine
├── templates/
│   └── index.html       # Web UI (dark glassmorphism)
├── requirements.txt
└── .env.example
```

---

## 🛡️ Usage Notes

- Use **Google Chrome** for best voice recognition support
- Microphone permission must be allowed in the browser
- Model files (`yolov8n.pt`, `hand_landmarker.task`) are excluded from this repo due to size — download them as shown above

---

## 👨‍💻 Author

**Arpit Sharma** · [@PILOT-SHARMA](https://github.com/PILOT-SHARMA)

---

## 📄 License

MIT License — free to use, modify, and distribute.
