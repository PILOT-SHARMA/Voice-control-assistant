# 🎙️ Voice-Controlled Assistant

A Python-based voice assistant that listens to your voice commands and performs tasks like opening websites, telling the time, searching the web, playing music, and having natural conversations. **Now with a beautiful, Gemini-styled web interface!**

**Built for:** College Mini Project / Viva Presentation  
**Tech Stack:** Python, Flask, HTML/CSS/JS, SpeechRecognition, pyttsx3, datetime, webbrowser, os

---

## ✨ Features

| Feature | Example Command |
|---|---|
| 🌐 Open Websites | "Open YouTube", "Open Google" |
| 🕐 Tell Time | "What time is it?" |
| 📅 Tell Date | "What is today's date?" |
| 🔍 Web Search | "Search for Python tutorials" |
| 🎵 Play Music | "Play music", "Play a song" |
| 👋 Greetings | "Hello", "How are you?" |
| 🛑 Exit | "Stop", "Bye", "Goodbye" |
| 🗣️ Wake Word | "Hey Assistant" (optional) |

---

## 📁 Folder Structure

```
Voice-assistant/
├── app.py                # NEW: Flask server for web UI
├── assistant.py          # Core logic and terminal app
├── requirements.txt      # Dependencies list
├── chat_history.json     # Auto-saves chat sessions
├── README.md             # Documentation
├── music/                # Put your .mp3 / .wav files here
│   └── .gitkeep
└── templates/
    └── index.html        # NEW: Beautiful frontend (HTML/CSS/JS)
```

---

## 🚀 How to Install and Run

### Prerequisites
- Python 3.8 or higher installed
- A working microphone
- Internet connection

### Step 1: Install Dependencies

Open a terminal in the project folder and run:
```bash
pip install -r requirements.txt
```

> **Note for macOS users:** If `PyAudio` fails to install, first run `brew install portaudio` then `pip install pyaudio`.

### Step 2: Add Music (Optional)

Place any `.mp3` or `.wav` files in the `music/` folder.

---

## 🌐 Running the Web Interface (NEW)

The easiest and best way to use the assistant!

1. Run the Flask server:
```bash
python app.py
```

2. Open your browser and go to:
[http://localhost:5000](http://localhost:5000)

3. Click the 🎤 microphone button or type a command.

*Features in Web UI:*
- Clean Gemini-like dark theme
- Persistent Chat History (Sidebar)
- Export chat logs as `.txt` files
- Fully responsive on mobile

---

## 🎤 Running the Terminal Version

You can still run the old terminal-only version if you prefer:
```bash
python assistant.py
```

Say **"Stop"** or **"Exit"** to quit.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| Microphone not working (Web) | Make sure you click "Allow" when the browser asks for microphone permission. |
| Microphone not working (Terminal) | Check permissions in System Settings → Privacy → Microphone |
| "Could not understand audio" | Speak clearly, reduce background noise |
| Internet error | Check your WiFi connection (Google API needs internet) |
| No music plays | Add `.mp3`/`.wav` files to the `music/` folder |

---

## 📄 License

This project is created for educational purposes. Feel free to use and modify it.
