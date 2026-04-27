"""
Voice-Controlled Assistant
==========================
A Python-based voice assistant that listens to your commands
and performs tasks like opening websites, telling time, playing music, etc.

Author : Arpit
Project: College Mini Project
"""

# ──────────────────────────────────────────────
# 1. IMPORT ALL REQUIRED LIBRARIES
# ──────────────────────────────────────────────

import speech_recognition as sr   # For converting speech to text
import pyttsx3                    # For converting text to speech (offline)
import datetime                   # For getting current date and time
import webbrowser                 # For opening websites in browser
import os                         # For interacting with the operating system
import random                     # For picking random responses
import sys                        # For exiting the program gracefully


# ──────────────────────────────────────────────
# 2. INITIALIZE THE TEXT-TO-SPEECH ENGINE
# ──────────────────────────────────────────────

engine = pyttsx3.init()

# Set speech rate (default ~200; lower = slower, higher = faster)
engine.setProperty('rate', 170)

# Set volume (0.0 to 1.0)
engine.setProperty('volume', 0.9)

# Optional: Choose a voice (0 = male, 1 = female on most systems)
voices = engine.getProperty('voices')
if len(voices) > 1:
    engine.setProperty('voice', voices[1].id)  # Female voice
else:
    engine.setProperty('voice', voices[0].id)  # Default voice


# ──────────────────────────────────────────────
# 3. HELPER FUNCTIONS
# ──────────────────────────────────────────────

def speak(text):
    """
    Convert text to speech and speak it out loud.
    Also prints the text to the console for reference.
    """
    print(f"🤖 Assistant: {text}")
    engine.say(text)
    engine.runAndWait()


def greet_user():
    """
    Greet the user based on the current time of day.
    - Morning   : 5 AM  – 12 PM
    - Afternoon : 12 PM – 5 PM
    - Evening   : 5 PM  – 9 PM
    - Night     : 9 PM  – 5 AM
    """
    hour = datetime.datetime.now().hour

    if 5 <= hour < 12:
        speak("Good morning! I'm your voice assistant. How can I help you today?")
    elif 12 <= hour < 17:
        speak("Good afternoon! I'm your voice assistant. What can I do for you?")
    elif 17 <= hour < 21:
        speak("Good evening! I'm your voice assistant. How may I assist you?")
    else:
        speak("Hello! It's late, but I'm here to help. What do you need?")
