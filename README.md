# 🎙️ Voice-Controlled Assistant

A Python-based voice assistant that listens to your voice commands and performs tasks like opening websites, telling the time, searching the web, playing music, and having natural conversations.

**Built for:** College Mini Project / Viva Presentation  
**Tech Stack:** Python, SpeechRecognition, pyttsx3, datetime, webbrowser, os

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
├── assistant.py          # Main Python file (all the code)
├── requirements.txt      # List of dependencies to install
├── README.md             # This file (project documentation)
└── music/                # Put your .mp3 / .wav files here
    └── .gitkeep          # Keeps the folder in version control
```

---

## 🚀 How to Install and Run

### Prerequisites
- Python 3.8 or higher installed ([Download Python](https://www.python.org/downloads/))
- A working microphone
- Internet connection (for Google Speech Recognition)

### Step 1: Open Terminal / Command Prompt

Navigate to the project folder:
```bash
cd /path/to/Voice-assistant
```

### Step 2: (Recommended) Create a Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note for macOS users:** If `PyAudio` fails to install, first run:
> ```bash
> brew install portaudio
> pip install pyaudio
> ```

> **Note for Windows users:** If `PyAudio` fails, try:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```

### Step 4: Add Music (Optional)

Place any `.mp3` or `.wav` files in the `music/` folder to use the "Play Music" feature.

### Step 5: Run the Assistant

```bash
python assistant.py
```

---

## 🎤 How to Use

1. Run the program — the assistant will greet you
2. Speak your command clearly into the microphone
3. Wait for the assistant to process and respond
4. Say **"Stop"** or **"Exit"** to quit

### Enable Wake Word (Optional)

In `assistant.py`, find this line inside `main()`:
```python
use_wake_word = False
```
Change it to:
```python
use_wake_word = True
```
Now the assistant will wait for **"Hey Assistant"** before listening to commands.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| Microphone not working | Check permissions in System Settings → Privacy → Microphone |
| PyAudio install error | Install `portaudio` first (see Step 3 notes above) |
| "Could not understand audio" | Speak clearly, reduce background noise |
| Internet error | Check your WiFi connection (Google API needs internet) |
| No music plays | Add `.mp3`/`.wav` files to the `music/` folder |

---

## 📚 Libraries Used

| Library | Purpose | Needs Internet? |
|---|---|---|
| `speech_recognition` | Convert voice → text | ✅ Yes |
| `pyttsx3` | Convert text → voice | ❌ No (offline) |
| `datetime` | Get current time/date | ❌ No |
| `webbrowser` | Open URLs in browser | ✅ Yes |
| `os` | File system operations | ❌ No |
| `random` | Random response selection | ❌ No |

---

## 📄 License

This project is created for educational purposes. Feel free to use and modify it.
