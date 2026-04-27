"""
Voice-Controlled Assistant
==========================
A Python-based voice assistant that listens to your commands
and performs tasks like opening websites, telling time, playing music, etc.

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

# Global flag for Wake Word (used by both terminal and web interfaces)
USE_WAKE_WORD = False

engine = pyttsx3.init()
engine.setProperty('rate', 170)
engine.setProperty('volume', 0.9)

voices = engine.getProperty('voices')
if len(voices) > 1:
    engine.setProperty('voice', voices[1].id)
else:
    engine.setProperty('voice', voices[0].id)

def speak(text):
    print(f"🤖 Assistant: {text}")
    engine.say(text)
    engine.runAndWait()

def greet_user():
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
    recognizer = sr.Recognizer()
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
        text = recognizer.recognize_google(audio, language='en-in')
        print(f"🗣️  You said: {text}")
        return text.lower()
    except sr.UnknownValueError:
        speak("Sorry, I didn't catch that. Could you please repeat?")
        return None
    except sr.RequestError:
        speak("I'm having trouble connecting to the internet. Please check your connection and try again.")
        return None

def tell_time():
    now = datetime.datetime.now()
    time_str = now.strftime("%I:%M %p")
    speak(f"The current time is {time_str}.")

def tell_date():
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    speak(f"Today is {date_str}.")

def open_website(command):
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
    for site_name, url in websites.items():
        if site_name in command:
            speak(f"Opening {site_name} for you.")
            webbrowser.open(url)
            return True
    return False

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
        "hello": ["Hello! Great to hear from you. What can I help with?", "Hey there! I'm ready to assist. What's on your mind?", "Hi! How can I make your day easier?"],
        "hi": ["Hi! What would you like me to do?", "Hey! I'm all ears. Go ahead!", "Hello there! How can I help?"],
        "how are you": ["I'm doing great, thanks for asking! How can I help you?", "I'm running perfectly! What can I do for you today?", "I'm wonderful! Ready to assist you with anything."],
        "good morning": ["Good morning! Hope you're having a great start to your day!", "Morning! What can I help you with today?"],
        "good afternoon": ["Good afternoon! How can I assist you?", "Afternoon! What would you like me to do?"],
        "good evening": ["Good evening! How may I help you tonight?", "Evening! What's on your mind?"],
        "good night": ["Good night! Sleep well and take care!", "Night night! Have sweet dreams!"],
        "thank you": ["You're welcome! Happy to help!", "Anytime! That's what I'm here for.", "My pleasure! Let me know if you need anything else."],
        "thanks": ["You're welcome!", "No problem at all!", "Glad I could help!"],
        "who are you": ["I'm your personal voice assistant, built with Python! I can open websites, tell time, search the web, and play music."],
        "what can you do": ["I can open websites like YouTube and Google, tell you the time and date, search the web for anything, play music from your computer, and have a friendly chat. Just ask!"],
        "what is your name": ["I'm your Voice Assistant! You can call me whatever you like.", "I don't have a fancy name, but I'm your helpful voice assistant!"],
    }
    for greeting, responses in greetings.items():
        if greeting in command:
            speak(random.choice(responses))
            return True
    return False

def process_command(command):
    if any(word in command for word in ["stop", "exit", "quit", "bye", "goodbye", "shut down"]):
        speak(random.choice(["Goodbye! Have a wonderful day!", "See you later! Take care!", "Bye bye! It was nice talking to you!", "Shutting down. Have a great day ahead!"]))
        return False
    if "open" in command:
        if open_website(command): return True
    if any(word in command for word in ["time", "what time", "current time"]):
        tell_time(); return True
    if any(word in command for word in ["date", "today's date", "what date", "what day"]):
        tell_date(); return True
    if any(word in command for word in ["search", "look up", "find", "google"]):
        search_web(command); return True
    if any(word in command for word in ["play music", "play song", "play a song", "music"]):
        play_music(); return True
    if handle_greeting(command): return True

    speak(random.choice([
        "I'm not sure how to help with that. Could you try rephrasing?",
        "Hmm, I don't understand that command yet. Try something else!",
        "I'm still learning! I can open websites, tell time, search the web, or play music.",
        "Sorry, I didn't get that. You can ask me to open websites, tell time, or play music."
    ]))
    return True

# ──────────────────────────────────────────────
# NEW WEB COMMAND PROCESSOR
# ──────────────────────────────────────────────
def process_command_web(command):
    """
    Same logic as process_command, but instead of calling speak(),
    it returns the text response and action type for the web interface.
    """
    if any(word in command for word in ["stop", "exit", "quit", "bye", "goodbye", "shut down"]):
        farewell_messages = [
            "Goodbye! Have a wonderful day!",
            "See you later! Take care!",
            "Bye bye! It was nice talking to you!",
            "Shutting down. Have a great day ahead!",
        ]
        return {"response": random.choice(farewell_messages), "action": "exit"}

    if "open" in command:
        websites = {
            "youtube": "https://www.youtube.com", "google": "https://www.google.com",
            "gmail": "https://mail.google.com", "github": "https://www.github.com",
            "wikipedia": "https://www.wikipedia.org", "instagram": "https://www.instagram.com",
            "facebook": "https://www.facebook.com", "twitter": "https://www.twitter.com",
            "linkedin": "https://www.linkedin.com", "whatsapp": "https://web.whatsapp.com",
            "chat gpt": "https://chat.openai.com", "chatgpt": "https://chat.openai.com",
            "stack overflow": "https://stackoverflow.com", "stackoverflow": "https://stackoverflow.com"
        }
        for site_name, url in websites.items():
            if site_name in command:
                webbrowser.open(url)
                return {"response": f"Opening {site_name} for you.", "action": "open_website"}

    if any(word in command for word in ["time", "what time", "current time"]):
        now = datetime.datetime.now()
        return {"response": f"The current time is {now.strftime('%I:%M %p')}.", "action": "speak"}

    if any(word in command for word in ["date", "today's date", "what date", "what day"]):
        now = datetime.datetime.now()
        return {"response": f"Today is {now.strftime('%A, %B %d, %Y')}.", "action": "speak"}

    if any(word in command for word in ["search", "look up", "find", "google"]):
        search_terms = command
        for phrase in ["search for", "search", "look up", "google", "find"]:
            search_terms = search_terms.replace(phrase, "")
        search_terms = search_terms.strip()

        if search_terms:
            webbrowser.open(f"https://www.google.com/search?q={search_terms}")
            return {"response": f"Searching the web for: {search_terms}", "action": "search"}
        else:
            return {"response": "What would you like me to search for?", "action": "speak"}

    if any(word in command for word in ["play music", "play song", "play a song", "music"]):
        music_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")
        if not os.path.exists(music_dir):
            return {"response": "I couldn't find the music folder. Please create a folder named 'music' and add some songs to it.", "action": "speak"}
        
        supported_formats = ('.mp3', '.wav', '.m4a', '.ogg', '.flac')
        songs = [f for f in os.listdir(music_dir) if f.lower().endswith(supported_formats)]
        if not songs:
            return {"response": "The music folder is empty. Please add some songs to it first.", "action": "speak"}
        
        song = random.choice(songs)
        song_path = os.path.join(music_dir, song)
        
        if sys.platform == "darwin":
            os.system(f'open "{song_path}"')
        elif sys.platform == "win32":
            os.startfile(song_path)
        else:
            os.system(f'xdg-open "{song_path}"')
            
        return {"response": f"Playing {os.path.splitext(song)[0]} for you. Enjoy!", "action": "music"}

    greetings = {
        "hello": ["Hello! Great to hear from you. What can I help with?", "Hey there! I'm ready to assist. What's on your mind?", "Hi! How can I make your day easier?"],
        "hi": ["Hi! What would you like me to do?", "Hey! I'm all ears. Go ahead!", "Hello there! How can I help?"],
        "how are you": ["I'm doing great, thanks for asking! How can I help you?", "I'm running perfectly! What can I do for you today?", "I'm wonderful! Ready to assist you with anything."],
        "good morning": ["Good morning! Hope you're having a great start to your day!", "Morning! What can I help you with today?"],
        "good afternoon": ["Good afternoon! How can I assist you?", "Afternoon! What would you like me to do?"],
        "good evening": ["Good evening! How may I help you tonight?", "Evening! What's on your mind?"],
        "good night": ["Good night! Sleep well and take care!", "Night night! Have sweet dreams!"],
        "thank you": ["You're welcome! Happy to help!", "Anytime! That's what I'm here for.", "My pleasure! Let me know if you need anything else."],
        "thanks": ["You're welcome!", "No problem at all!", "Glad I could help!"],
        "who are you": ["I'm your personal voice assistant, built with Python! I can open websites, tell time, search the web, and play music."],
        "what can you do": ["I can open websites like YouTube and Google, tell you the time and date, search the web for anything, play music from your computer, and have a friendly chat. Just ask!"],
        "what is your name": ["I'm your Voice Assistant! You can call me whatever you like.", "I don't have a fancy name, but I'm your helpful voice assistant!"],
    }
    for greeting, responses in greetings.items():
        if greeting in command:
            return {"response": random.choice(responses), "action": "speak"}

    unknown_responses = [
        "I'm not sure how to help with that. Could you try rephrasing?",
        "Hmm, I don't understand that command yet. Try something else!",
        "I'm still learning! I can open websites, tell time, search the web, or play music.",
        "Sorry, I didn't get that. You can ask me to open websites, tell time, or play music."
    ]
    return {"response": random.choice(unknown_responses), "action": "speak"}

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
    except (sr.UnknownValueError, sr.RequestError):
        return False

def main():
    print("=" * 55)
    print("   🎙️  VOICE-CONTROLLED ASSISTANT  🎙️")
    print("=" * 55)
    print("   Commands you can try:")
    print("   • 'Open YouTube / Google / Gmail'")
    print("   • 'What time is it?'")
    print("   • 'What is today's date?'")
    print("   • 'Search for Python tutorials'")
    print("   • 'Play music'")
    print("   • 'Hello / How are you?'")
    print("   • 'Stop' to exit")
    print("=" * 55)

    greet_user()
    running = True

    while running:
        try:
            if USE_WAKE_WORD:
                wake_detected = listen_for_wake_word()
                if not wake_detected:
                    continue

            command = listen()
            if command is None:
                continue

            for wake in ["hey assistant", "hello assistant", "ok assistant"]:
                command = command.replace(wake, "").strip()

            if not command:
                continue

            running = process_command(command)

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
