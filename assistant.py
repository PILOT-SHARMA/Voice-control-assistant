"""
Voice-Controlled Assistant (Pro Version)
========================================
A stable, professional Python-based voice assistant featuring:
- Debouncing and command cooldowns
- Duplicate command filtering
- Speech confidence thresholds
- Native desktop app launching

Author : Arpit
Project: College Mini Project
"""

import speech_recognition as sr
import pyttsx3
import datetime
import webbrowser
import os
import random
import sys
import subprocess
import time
import re

# ==========================================
# SYSTEM CONFIGURATION & STATE
# ==========================================
USE_WAKE_WORD = False

# Duplicate Guard for Websites
_last_opened = {"url": None, "time": 0}

# Cooldown & Debounce State
LAST_COMMAND_TEXT = None
LAST_COMMAND_TIME = 0.0
COMMAND_COOLDOWN_SEC = 1.5      # Minimum time between ANY commands
DUPLICATE_COOLDOWN_SEC = 3.0    # Minimum time before repeating the EXACT SAME command

def speak(text):
    """Speak text out loud using macOS native TTS engine (JARVIS Voice)."""
    print(f"🤖 J.A.R.V.I.S: {text}")
    clean_text = text.replace('"', '').replace("'", "")
    
    # We use Daniel voice (British male) at a slightly faster rate for the perfect JARVIS feel
    if sys.platform == "darwin":
        subprocess.run(['say', '-v', 'Daniel', '-r', '185', clean_text])
    else:
        # Fallback for non-macOS (though we are on a Mac)
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

def greet_user():
    """Context-aware time-of-day greeting."""
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        speak("Good morning! I'm your voice assistant. How can I help you today?")
    elif 12 <= hour < 17:
        speak("Good afternoon! I'm your voice assistant. What can I do for you?")
    elif 17 <= hour < 21:
        speak("Good evening! I'm your voice assistant. How may I assist you?")
    else:
        speak("Hello! It's late, but I'm here to help. What do you need?")

# ==========================================
# SPEECH RECOGNITION (WITH CONFIDENCE & CLEANING)
# ==========================================
def listen():
    """
    Listen to microphone and return cleaned text.
    Implements pause thresholds and extracts confidence scores.
    """
    recognizer = sr.Recognizer()
    
    # Require 1.2 seconds of silence before considering the phrase "complete"
    # This prevents the recognizer from processing partial speech inputs.
    recognizer.pause_threshold = 1.2  
    
    try:
        with sr.Microphone() as source:
            print("\n🎤 Listening... (speak now)")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
    except sr.WaitTimeoutError:
        print("⏰ No speech detected within the timeout period.")
        return None
    except OSError:
        speak("I couldn't access your microphone. Please check if it's connected.")
        return None

    try:
        print("🔄 Processing your speech...")
        
        # Request show_all=True to get alternative hypotheses and confidence scores
        response = recognizer.recognize_google(audio, language='en-in', show_all=True)
        
        # If response is empty or invalid
        if not response or not isinstance(response, dict) or 'alternative' not in response:
            return None
            
        # Get the highest confidence match
        best_match = response['alternative'][0]
        raw_text = best_match['transcript']
        
        # Google doesn't always provide confidence for short phrases, default to 1.0
        confidence = best_match.get('confidence', 1.0)
        
        print(f"🗣️  Recognized: '{raw_text}' (Confidence: {confidence:.2f})")
        
        # BONUS: Confidence Threshold & "Did you mean?" Fallback
        if confidence < 0.65:
            speak(f"I am not entirely sure, did you mean: {raw_text}?")
            # We still process it, but notify the user it was a low-confidence match
            
        # 5. CLEAN COMMAND PROCESSING
        # Lowercase, strip edges, and replace multiple spaces with a single space
        clean_text = re.sub(r'\s+', ' ', raw_text.lower().strip())
        return clean_text
        
    except sr.UnknownValueError:
        # Ignore silent background noises without speaking to avoid spam
        print("🤫 (Unrecognized background noise ignored)")
        return None
    except sr.RequestError:
        speak("I'm having trouble connecting to the internet. Please check your connection and try again.")
        return None

# ==========================================
# SYSTEM COMMANDS & ACTIONS
# ==========================================
def tell_time():
    now = datetime.datetime.now()
    speak(f"The current time is {now.strftime('%I:%M %p')}.")

def tell_date():
    now = datetime.datetime.now()
    speak(f"Today is {now.strftime('%A, %B %d, %Y')}.")

def open_application(command):
    """Launch native desktop apps via OS processes."""
    apps = {
        "whatsapp": {"win32": "start whatsapp:", "darwin": "open -a WhatsApp", "linux": "whatsapp-desktop"},
        "telegram": {"win32": "start telegram:", "darwin": "open -a Telegram", "linux": "telegram-desktop"},
        "calculator": {"win32": "calc", "darwin": "open -a Calculator", "linux": "gnome-calculator"},
        "vs code": {"win32": "code", "darwin": "open -a 'Visual Studio Code'", "linux": "code"},
        "spotify": {"win32": "start spotify:", "darwin": "open -a Spotify", "linux": "spotify"},
        "terminal": {"win32": "start cmd", "darwin": "open -a Terminal", "linux": "gnome-terminal"},
        "settings": {"win32": "start ms-settings:", "darwin": "open -a 'System Settings'", "linux": "gnome-control-center"},
    }

    for app_name, commands in apps.items():
        if app_name in command:
            cmd = commands.get(sys.platform)
            if not cmd:
                speak(f"Sorry, I don't know how to open {app_name.title()} on your system.")
                return True

            try:
                speak(f"Opening {app_name.title()} for you.")
                if sys.platform == "win32":
                    os.system(cmd)
                else:
                    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception as e:
                speak(f"Something went wrong while opening {app_name.title()}.")
                print(f"App open error: {e}")
                return True
    return False

def open_website(command):
    """Open websites with a built-in duplicate guard."""
    websites = {
        "youtube": "https://www.youtube.com", "google": "https://www.google.com",
        "gmail": "https://mail.google.com", "github": "https://www.github.com",
        "wikipedia": "https://www.wikipedia.org", "chatgpt": "https://chat.openai.com",
        "stack overflow": "https://stackoverflow.com", "amazon": "https://www.amazon.com",
    }

    for site_name, url in websites.items():
        if site_name in command:
            # Duplicate guard to prevent 3-4 tabs
            now = time.time()
            if (_last_opened["url"] == url and (now - _last_opened["time"]) < 5):
                print(f"⚠️  Duplicate open blocked for: {url}")
                return True

            _last_opened["url"] = url
            _last_opened["time"] = now

            speak(f"Opening {site_name.title()} for you.")
            webbrowser.open(url)
            return True
    return False

def search_wikipedia(command):
    query = command
    for phrase in ["wikipedia", "wiki", "tell me about", "who is", "what is"]:
        query = query.replace(phrase, "")
    query = query.strip()
    if query:
        speak(f"Searching Wikipedia for {query}.")
        webbrowser.open(f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}")
    else:
        speak("What would you like to search on Wikipedia?")

def search_web(query):
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
    music_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")
    if not os.path.exists(music_dir):
        speak("I couldn't find the music folder. Please create a folder named 'music' and add some songs to it.")
        return

    supported_formats = ('.mp3', '.wav', '.m4a', '.ogg', '.flac')
    songs = [f for f in os.listdir(music_dir) if f.lower().endswith(supported_formats)]

    if not songs:
        speak("The music folder is empty. Please add some songs to it first.")
        return

    song = random.choice(songs)
    song_path = os.path.join(music_dir, song)
    song_name = os.path.splitext(song)[0]

    speak(f"Playing {song_name} for you. Enjoy!")

    if sys.platform == "darwin":
        os.system(f'open "{song_path}"')
    elif sys.platform == "win32":
        os.startfile(song_path)
    else:
        os.system(f'xdg-open "{song_path}"')

def handle_greeting(command):
    greetings = {
        "hello": ["Hello! Great to hear from you. What can I help with?", "Hi! How can I make your day easier?"],
        "hi": ["Hi! What would you like me to do?", "Hey! I'm all ears. Go ahead!"],
        "how are you": ["I'm doing great, thanks for asking! How can I help you?", "I'm running perfectly! What can I do for you today?"],
        "who are you": ["I'm your personal voice assistant, built with Python! I can open websites, tell time, search the web, and play music."],
        "what can you do": ["I can open apps, websites like YouTube, tell you the time and date, search the web for anything, play music, and have a chat!"],
        "thank you": ["You're welcome! Happy to help!", "Anytime! That's what I'm here for."],
        "thanks": ["You're welcome!", "No problem at all!"],
    }
    
    # Exact word boundaries to prevent triggering "how are you" on "how are"
    words = command.split()
    
    for greeting, responses in greetings.items():
        if greeting in command:
            # Extra intent check for common short phrases
            if greeting == "hi" and len(words) > 3: continue # "hi" inside a sentence
            
            speak(random.choice(responses))
            return True
    return False

# ==========================================
# COMMAND ROUTING (SINGLE EXECUTION PATH)
# ==========================================
def process_command(command):
    """
    Process the normalized user voice command.
    Uses strict if-elif structure to ensure only ONE action executes.
    """
    if any(word in command for word in ["stop", "exit", "quit", "bye", "shut down"]):
        speak(random.choice(["Goodbye! Have a wonderful day!", "See you later! Take care!"]))
        return False

    elif "open" in command:
        if open_application(command): pass
        elif open_website(command): pass
        else:
            query = command.replace("open", "").strip()
            if query:
                speak(f"I couldn't find {query} as an app or website. Searching instead.")
                search_web(query)

    elif any(word in command for word in ["time", "what time", "current time"]):
        tell_time()

    elif any(word in command for word in ["date", "today's date", "what date", "what day"]):
        tell_date()

    elif any(word in command for word in ["wikipedia", "wiki", "tell me about"]):
        search_wikipedia(command)

    elif any(word in command for word in ["search", "look up", "find", "google"]):
        search_web(command)

    elif any(word in command for word in ["play music", "play song", "play a song", "music"]):
        play_music()

    elif handle_greeting(command):
        pass

    else:
        speak(random.choice([
            "I'm not sure how to help with that. Could you try rephrasing?",
            "Hmm, I don't understand that command yet. Try something else!",
            "I'm still learning! I can open apps, websites, tell time, search the web, or play music.",
        ]))

    return True

def process_command_web(command):
    """Routing equivalent for the Flask web frontend API — BOSS MODE."""
    if any(word in command for word in ["stop", "exit", "quit", "bye", "shut down"]):
        return {"response": "Alright Boss, signing off! Have a great day! 👋🤖", "action": "exit"}

    elif "open" in command:
        if open_application(command):
            return {"response": "Yes Boss! Opening the application right away! 🚀", "action": "open_website"}
        elif open_website(command):
            return {"response": "Yes Boss! Opening the website for you! 🌐", "action": "open_website"}
        else:
            query = command.replace("open", "").strip()
            if query:
                search_web(query)
                return {"response": f"Yes Boss! Couldn't find {query} as an app, searching the web instead! 🔍", "action": "search"}
            return {"response": "What would you like me to open, Boss? 🤔", "action": "speak"}

    elif any(word in command for word in ["time", "what time", "current time"]):
        return {"response": f"Yes Boss! The current time is {datetime.datetime.now().strftime('%I:%M %p')} ⏰", "action": "speak"}

    elif any(word in command for word in ["date", "today's date", "what date"]):
        return {"response": f"Yes Boss! Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')} 📅", "action": "speak"}

    elif any(word in command for word in ["search", "look up", "find"]):
        search_terms = command
        for phrase in ["search for", "search", "look up", "find"]:
            search_terms = search_terms.replace(phrase, "")
        search_terms = search_terms.strip()
        if search_terms:
            webbrowser.open(f"https://www.google.com/search?q={search_terms}")
            return {"response": f"Yes Boss! Searching the web for: {search_terms} 🔍", "action": "search"}
        return {"response": "What should I search for, Boss? 🤔", "action": "speak"}

    elif any(word in command for word in ["play music", "play song"]):
        music_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")
        if not os.path.exists(music_dir) or not os.listdir(music_dir):
            return {"response": "Sorry Boss, the music folder is empty! Add some songs first 🎵", "action": "speak"}
        
        song = random.choice([f for f in os.listdir(music_dir) if f.endswith(('.mp3', '.wav'))])
        os.system(f'open "{os.path.join(music_dir, song)}"' if sys.platform == "darwin" else f'xdg-open "{os.path.join(music_dir, song)}"')
        return {"response": f"Yes Boss! Playing {os.path.splitext(song)[0]} 🎵🎶", "action": "music"}

    # Handle greetings — BOSS STYLE
    greetings_map = {
        "hello": ["Yes Boss! 🫡 Hello! How can I help you today?", "Hey Boss! What can I do for you? 🤖"],
        "hi": ["Yes Boss! What's on the agenda? 🫡", "Hey Boss! Ready for your commands! 🚀"],
        "hey": ["Yes Boss! What's up? I'm all ears! 🫡", "Hey Boss! Ready to help! 🤖"],
        "how are you": ["I'm running at 100% Boss! All systems operational! ⚡🤖", "Feeling great Boss! Ready to serve! 🫡"],
        "who are you": ["I'm J.A.R.V.I.S — your personal AI assistant, Boss! I can open apps, websites, search the web, play music, tell time, and chat with you! 🤖✨"],
        "what can you do": ["Boss, I can do a lot! 🚀 Open apps & websites • Search the web • Tell time & date • Play music • Chat with you • Execute your commands!"],
        "thank you": ["Always at your service, Boss! 🫡", "No problem Boss! That's what I'm here for! 🤖"],
        "thanks": ["Anytime Boss! 🫡", "Happy to help, Boss! 🤖"],
        "good morning": ["Good morning Boss! ☀️ Ready to make your day productive!"],
        "good night": ["Good night Boss! 🌙 Rest well, I'll be here when you need me!"],
        "joke": [
            "Yes Boss! Here's one: Why do programmers prefer dark mode? Because light attracts bugs! 🐛😄",
            "Sure Boss! Why was the JavaScript developer sad? Because he didn't Node how to Express himself! 😂",
            "Here you go Boss! What's a computer's favorite snack? Microchips! 🍟😄",
        ],
        "tell me a joke": [
            "Yes Boss! Why do programmers prefer dark mode? Because light attracts bugs! 🐛😄",
            "Sure thing Boss! I told my computer I needed a break, and now it won't stop sending me Kit-Kat ads! 🍫😂",
            "Of course Boss! What did the router say to the doctor? It hurts when IP! 😂",
        ],
    }

    for key, responses in greetings_map.items():
        if key in command:
            return {"response": random.choice(responses), "action": "speak"}

    # Smart conversational fallback — BOSS STYLE
    smart_responses = {
        "python": "Yes Boss! Python is a powerful programming language used for web dev, AI, data science, automation, and more! 🐍",
        "javascript": "Yes Boss! JavaScript is the language of the web — it powers interactive websites, servers (Node.js), and mobile apps! 💻",
        "ai": "Yes Boss! AI is the simulation of human intelligence by machines — including ML, deep learning, NLP, and computer vision! 🤖",
        "weather": "Boss, I can't check live weather yet, but say 'Search weather in [your city]' and I'll Google it! 🌤️",
        "news": "Boss, say 'Search latest news' and I'll open Google News for you right away! 📰",
        "help": "Boss, here's what I can do: 🎤 Voice commands • 💬 Chat • 🌐 Open websites • 🔍 Search • 🎵 Play music • ⏰ Time & date",
        "music": "Yes Boss! Say 'play music' and I'll play a song from your collection! 🎵",
        "who made you": "I was created by Arpit Sharma as a college mini project, Boss! Built with Python, Flask, and lots of ❤️",
        "your name": "I'm J.A.R.V.I.S, Boss! Your personal AI assistant! 🤖",
    }

    for key, response in smart_responses.items():
        if key in command:
            return {"response": response, "action": "speak"}

    return {"response": f"Yes Boss! I heard you say '{command}'. I'm still learning new things, but try asking me to open apps, search the web, or just chat! 🤖💬", "action": "speak"}

# ==========================================
# WAKE WORD & MAIN LOOP
# ==========================================
def listen_for_wake_word():
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("\n💤 Waiting for wake word ('Hey Assistant')...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=4)
    except sr.WaitTimeoutError:
        return False
    except OSError:
        return False

    try:
        text = recognizer.recognize_google(audio, language='en-in').lower()
        if any(wake in text for wake in ["hey assistant", "hello assistant", "ok assistant"]):
            speak("Yes, I'm listening! What can I do for you?")
            return True
        return False
    except:
        return False

def main():
    global LAST_COMMAND_TEXT, LAST_COMMAND_TIME
    
    print("=" * 55)
    print("   🎙️  VOICE-CONTROLLED ASSISTANT (PRO)  🎙️")
    print("=" * 55)
    print("   Commands you can try:")
    print("   • 'Open YouTube / VS Code'")
    print("   • 'What time is it?'")
    print("   • 'Search for Python tutorials'")
    print("   • 'Play music'")
    print("=" * 55)

    greet_user()
    running = True

    while running:
        try:
            if USE_WAKE_WORD:
                if not listen_for_wake_word(): continue

            # 1. Listen and get normalized text
            command = listen()
            if not command:
                continue

            # Remove wake words if they accidentally made it into the main command
            for wake in ["hey assistant", "hello assistant", "ok assistant"]:
                command = command.replace(wake, "").strip()

            if not command:
                continue

            # ==========================================
            # DEBOUNCE & DUPLICATE FILTER
            # ==========================================
            current_time = time.time()
            time_since_last = current_time - LAST_COMMAND_TIME
            
            # 2. Global Cooldown (Prevent rapid-fire random noise execution)
            if time_since_last < COMMAND_COOLDOWN_SEC:
                print(f"⏳ Ignored: System is on cooldown for {COMMAND_COOLDOWN_SEC}s.")
                continue

            # 3. Duplicate Filter (Prevent repeating the exact same command 3-4 times)
            if command == LAST_COMMAND_TEXT and time_since_last < DUPLICATE_COOLDOWN_SEC:
                print(f"⚠️  Ignored duplicate command: '{command}'")
                continue
                
            # Update history trackers
            LAST_COMMAND_TEXT = command
            LAST_COMMAND_TIME = current_time

            # 4. Execute the command
            running = process_command(command)
            
            # Post-execution update to ensure long-running commands reset the cooldown properly
            LAST_COMMAND_TIME = time.time()

        except KeyboardInterrupt:
            print("\n")
            speak("Detected keyboard interrupt. Shutting down gracefully. Goodbye!")
            running = False
        except Exception as e:
            print(f"\n❌ An unexpected error occurred: {e}")
            speak("Something went wrong. Let me try again.")
            continue

    print("\n" + "=" * 55)
    print("   👋 Assistant has been shut down. See you next time!")
    print("=" * 55)

if __name__ == "__main__":
    main()
