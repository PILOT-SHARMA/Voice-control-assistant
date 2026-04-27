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


def listen():
    """
    Listen to the user's voice through the microphone and
    convert it to text using Google's free Speech Recognition API.

    Returns:
        str: The recognized text in lowercase, or None if not understood.
    """
    recognizer = sr.Recognizer()

    # Use the default microphone as the audio source
    try:
        with sr.Microphone() as source:
            print("\n🎤 Listening... (speak now)")

            # Adjust for background noise (takes ~1 second)
            recognizer.adjust_for_ambient_noise(source, duration=1)

            # Listen to the user (timeout after 5 sec, phrase limit 8 sec)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)

    except sr.WaitTimeoutError:
        print("⏰ No speech detected within the timeout period.")
        return None
    except OSError:
        speak("I couldn't access your microphone. Please check if it's connected.")
        return None

    # Try to recognize what the user said
    try:
        print("🔄 Processing your speech...")
        text = recognizer.recognize_google(audio, language='en-in')
        print(f"🗣️  You said: {text}")
        return text.lower()

    except sr.UnknownValueError:
        # Could not understand the audio
        speak("Sorry, I didn't catch that. Could you please repeat?")
        return None

    except sr.RequestError:
        # No internet or Google API issue
        speak("I'm having trouble connecting to the internet. "
              "Please check your connection and try again.")
        return None


def tell_time():
    """Tell the current time in a natural way."""
    now = datetime.datetime.now()
    time_str = now.strftime("%I:%M %p")  # e.g., "02:30 PM"
    speak(f"The current time is {time_str}.")


def tell_date():
    """Tell today's date in a natural way."""
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")  # e.g., "Monday, April 27, 2026"
    speak(f"Today is {date_str}.")


def open_website(command):
    """
    Open a website based on the user's command.
    Supports common websites and also custom URLs.
    """
    # Dictionary of common websites
    websites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "github": "https://www.github.com",
        "wikipedia": "https://www.wikipedia.org",
        "instagram": "https://www.instagram.com",
        "facebook": "https://www.facebook.com",
        "twitter": "https://www.twitter.com",
        "linkedin": "https://www.linkedin.com",
        "whatsapp": "https://web.whatsapp.com",
        "chat gpt": "https://chat.openai.com",
        "chatgpt": "https://chat.openai.com",
        "stack overflow": "https://stackoverflow.com",
        "stackoverflow": "https://stackoverflow.com",
    }

    # Check if the user mentioned any known website
    for site_name, url in websites.items():
        if site_name in command:
            speak(f"Opening {site_name} for you.")
            webbrowser.open(url)
            return True

    return False


def search_web(query):
    """
    Perform a Google search for the given query.
    Cleans up the query by removing trigger words.
    """
    # Remove common trigger phrases to get the actual search query
    search_terms = query
    for phrase in ["search for", "search", "look up", "google", "find"]:
        search_terms = search_terms.replace(phrase, "")

    search_terms = search_terms.strip()

    if search_terms:
        speak(f"Searching the web for: {search_terms}")
        url = f"https://www.google.com/search?q={search_terms}"
        webbrowser.open(url)
    else:
        speak("What would you like me to search for?")


def play_music():
    """
    Play a random music file from the 'music' folder.
    Supports .mp3 and .wav files.
    """
    # Path to the music folder (inside the project directory)
    music_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")

    # Check if the music folder exists
    if not os.path.exists(music_dir):
        speak("I couldn't find the music folder. "
              "Please create a folder named 'music' and add some songs to it.")
        return

    # Get list of audio files
    supported_formats = ('.mp3', '.wav', '.m4a', '.ogg', '.flac')
    songs = [f for f in os.listdir(music_dir) if f.lower().endswith(supported_formats)]

    if not songs:
        speak("The music folder is empty. Please add some songs to it first.")
        return

    # Pick a random song and play it
    song = random.choice(songs)
    song_path = os.path.join(music_dir, song)
    song_name = os.path.splitext(song)[0]  # Remove file extension for display

    speak(f"Playing {song_name} for you. Enjoy!")

    # Open the song with the default media player
    if sys.platform == "darwin":        # macOS
        os.system(f'open "{song_path}"')
    elif sys.platform == "win32":       # Windows
        os.startfile(song_path)
    else:                                # Linux
        os.system(f'xdg-open "{song_path}"')
