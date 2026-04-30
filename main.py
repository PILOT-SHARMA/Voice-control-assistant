"""
Main Entry Point — Real-Time AI Voice Assistant for Blind Users
================================================================
Initializes all subsystems (camera, voice, modes) and runs the
assistant in either terminal mode or web server mode.

Usage:
    python main.py              # Web server mode (Flask UI - DEFAULT)
    python main.py --terminal   # Terminal mode (voice only)

Author : Arpit
Project: Real-Time AI Voice Assistant for Blind Users
"""

import sys
import argparse
import threading
import time


def run_terminal_mode():
    """Run the assistant in terminal mode with voice I/O."""
    from camera import VisionSystem
    from assistant import speak, speak_sync, mode_manager, main_loop

    print("=" * 60)
    print("   👁️  REAL-TIME AI ASSISTANT FOR BLIND USERS  👁️")
    print("=" * 60)
    print("   Mode: STRICT VOICE CONTROL")
    print("   State: IDLE (Waiting for 'activate')")
    print("   ─────────────────────────────────────────────")
    print("   Voice Commands:")
    print("   • 'activate'               → Starts system & camera")
    print("   • 'deactivate'             → Stops system & camera")
    print("   • 'what is in my hand'     → Checks for held objects")
    print("   • 'what is in front of me' → Identifies object ahead")
    print("   • 'can i move forward'     → Checks if path is clear")
    print("=" * 60)

    # Initialize vision system with speak callback
    vision = VisionSystem(speak_callback=speak)
    mode_manager.set_vision_system(vision)

    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        vision.stop()
        print("\n👋 Assistant shut down. Goodbye!")


def run_web_mode():
    """Run the assistant as a Flask web server."""
    from camera import VisionSystem
    from assistant import speak, mode_manager

    # Initialize vision system
    vision = VisionSystem(speak_callback=speak)
    mode_manager.set_vision_system(vision)

    # Import and start Flask app
    from app import app

    print("=" * 60)
    print("   👁️  REAL-TIME AI ASSISTANT FOR BLIND USERS  👁️")
    print("=" * 60)
    print("   Mode: WEB SERVER")
    print("   Access UI at: http://localhost:5001")
    print("=" * 60)

    app.run(debug=False, port=5001, use_reloader=False, threaded=True)

    # Cleanup on exit
    vision.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Real-Time AI Voice Assistant for Blind Users"
    )
    parser.add_argument(
        "--terminal", action="store_true",
        help="Run in terminal mode (voice only) instead of web server mode"
    )
    args = parser.parse_args()

    if args.terminal:
        run_terminal_mode()
    else:
        run_web_mode()
