"""
Vision System — Real-Time Object Detection for Blind Users
===========================================================
Uses YOLOv8 (ultralytics) with webcam to detect objects,
estimate position (left/center/right) and distance (near/medium/far),
then produce natural-language navigation alerts.

Features:
  • Continuous frame capture via OpenCV
  • YOLOv8n (nano) for fast inference
  • Smart deduplication — only announces NEW or MOVED objects
  • Thread-safe callback system for TTS integration
  • Three modes: vision (continuous), navigation (obstacles only), off

Author : Arpit
"""

import cv2
import time
import threading
import datetime
from collections import defaultdict, deque
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# ─────────────────────────────────────────────
# TRY TO IMPORT ULTRALYTICS (YOLOv8)
# ─────────────────────────────────────────────
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️  ultralytics not installed. Run: pip install ultralytics")

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

# Objects considered obstacles/dangerous for navigation
OBSTACLE_CLASSES = {
    "car", "truck", "bus", "motorcycle", "bicycle",
    "dog", "cat", "horse",
    "fire hydrant", "stop sign", "traffic light",
    "bench", "chair", "couch", "dining table",
    "suitcase", "backpack", "bed", "toilet",
    "skateboard", "snowboard", "surfboard",
    "potted plant", "parking meter",
}

# Small objects that can be held in hand
HOLDABLE_OBJECTS = {
    "bottle", "cup", "cell phone", "remote", "scissors",
    "toothbrush", "knife", "fork", "spoon", "book",
    "apple", "banana", "orange", "sandwich", "donut",
    "mouse", "keyboard", "umbrella", "handbag",
}

# Minimum confidence threshold for detections
CONFIDENCE_THRESHOLD = 0.40

# How long (seconds) before re-announcing the SAME scene signature
ANNOUNCE_COOLDOWN = 8.0

# Frame processing interval (seconds)
FRAME_INTERVAL = 1.5


class VisionSystem:
    """
    Manages the webcam, runs YOLOv8 inference, and generates
    navigation-friendly spoken descriptions for blind users.
    """

    def __init__(self, speak_callback=None):
        """
        Args:
            speak_callback: A callable(text: str) that queues text for TTS.
        """
        self.speak = speak_callback or (lambda t: print(f"[VISION] {t}"))

        # State
        self._running = False
        self._thread = None
        self._cap = None
        self._mode = "off"          # "off" | "vision" | "navigation"
        self._lock = threading.Lock()

        # Smart filtering: tracks {(class_name, zone): last_announce_time}
        self._announced = defaultdict(float)

        # Load YOLOv8 model (nano for speed)
        self._model = None
        if YOLO_AVAILABLE:
            try:
                self._model = YOLO("yolov8n.pt")  # auto-downloads ~6 MB
                print("✅ YOLOv8n model loaded successfully.")
            except Exception as e:
                print(f"❌ Failed to load YOLO model: {e}")

        # Load MediaPipe Hands (Tasks API)
        try:
            base_options = mp_python.BaseOptions(model_asset_path='hand_landmarker.task')
            options = mp_vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=2,
                min_hand_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.hand_landmarker = mp_vision.HandLandmarker.create_from_options(options)
            print("✅ MediaPipe Hand Landmarker loaded successfully.")
        except Exception as e:
            self.hand_landmarker = None
            print(f"❌ Failed to load Hand Landmarker: {e}")

        # Latest frame for UI display (thread-safe)
        self._latest_frame = None
        self._frame_lock = threading.Lock()

        # Detection event log (for UI polling)
        self._detection_log = deque(maxlen=50)
        self._log_lock = threading.Lock()

        # Latest detections for direction indicators
        self._latest_detections = []
        self._latest_hand_results = None
        self._latest_frame_shape = None
        self._det_lock = threading.Lock()

        # Auto-start camera immediately
        self._start("vision")

    # ─────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────

    @property
    def mode(self):
        return self._mode

    @property
    def is_running(self):
        return self._running

    def start_vision_mode(self):
        """Start continuous detection (all objects)."""
        self._start("vision")

    def start_navigation_mode(self):
        """Start navigation mode (obstacles + path guidance)."""
        self._start("navigation")

    def stop(self):
        """Stop the camera and detection loop."""
        with self._lock:
            if not self._running:
                return
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._release_camera()
        if hasattr(self, 'hand_landmarker') and self.hand_landmarker:
            self.hand_landmarker.close()
        self._mode = "off"
        print("📷 Camera stopped.")

    def query_hand(self):
        with self._det_lock:
            hand_results = getattr(self, '_latest_hand_results', None)
            objects = list(self._latest_detections)
            frame_shape = getattr(self, '_latest_frame_shape', None)

        # --- Strategy 1: MediaPipe bounding box overlap ---
        if frame_shape and hand_results and hand_results.hand_landmarks:
            h, w = frame_shape[:2]
            for hand_landmarks, handedness in zip(hand_results.hand_landmarks, hand_results.handedness):
                hand_label = handedness[0].category_name  # "Left" or "Right"
                x_min = min(lm.x for lm in hand_landmarks) * w
                y_min = min(lm.y for lm in hand_landmarks) * h
                x_max = max(lm.x for lm in hand_landmarks) * w
                y_max = max(lm.y for lm in hand_landmarks) * h
                for obj in objects:
                    if obj['class'] == 'person':
                        continue
                    ox1, oy1, ox2, oy2 = obj['bbox']
                    if x_min < ox2 and x_max > ox1 and y_min < oy2 and y_max > oy1:
                        return f"You are holding a {obj['class']}"

        # --- Strategy 2: Fallback — very close holdable object ---
        for obj in objects:
            if obj['distance'] == 'very close' and obj['class'] in HOLDABLE_OBJECTS:
                return f"You are holding a {obj['class']}"

        return "I cannot detect anything"

    def query_front(self):
        with self._det_lock:
            objects = list(self._latest_detections)

        # Priority: closest + center object, ignore person far away
        center = [
            obj for obj in objects
            if obj['zone'] == 'center' and obj['class'] != 'person'
        ]
        # Sort by area ratio (larger = closer)
        center.sort(key=lambda o: o.get('area_ratio', 0), reverse=True)

        if not center:
            # fallback: nearest object in any zone
            non_person = [o for o in objects if o['class'] != 'person']
            non_person.sort(key=lambda o: o.get('area_ratio', 0), reverse=True)
            if non_person:
                return f"{non_person[0]['class']} in front of you"
            return "I cannot detect anything"

        return f"{center[0]['class']} in front of you"

    def query_path(self):
        with self._det_lock:
            objects = list(self._latest_detections)

        for obj in objects:
            if obj['zone'] == 'center' and obj['distance'] in ('very close', 'near') and obj['class'] != 'person':
                return "No, obstacle ahead"

        return "Yes, path is clear"

    def query_person_holding(self):
        """Detect what a nearby person is holding."""
        with self._det_lock:
            hand_results = getattr(self, '_latest_hand_results', None)
            objects = list(self._latest_detections)
            frame_shape = getattr(self, '_latest_frame_shape', None)

        # Find a person that is NOT very close (i.e. in front, not the user)
        person_objs = [o for o in objects if o['class'] == 'person' and o['distance'] != 'very close']
        if not person_objs:
            return "I cannot see a person in front"

        person = person_objs[0]  # take the nearest/most prominent
        px1, py1, px2, py2 = person['bbox']

        # Expand bbox slightly to capture hand-held items near the person
        margin = 40
        epx1, epy1, epx2, epy2 = px1 - margin, py1 - margin, px2 + margin, py2 + margin

        for obj in objects:
            if obj['class'] == 'person':
                continue
            ox1, oy1, ox2, oy2 = obj['bbox']
            # Check if object is inside or near the person's bounding box
            if ox1 < epx2 and ox2 > epx1 and oy1 < epy2 and oy2 > epy1:
                return f"The person in front is holding a {obj['class']}"

        return "I cannot tell what the person is holding"

    def get_latest_frame(self):
        """Return the most recent annotated frame (for UI display)."""
        with self._frame_lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def get_detection_log(self, count=20):
        """Return recent detection events as list of dicts."""
        with self._log_lock:
            return list(self._detection_log)[-count:]

    def get_latest_detections(self):
        """Return the latest frame's raw detections for UI direction indicators."""
        with self._det_lock:
            return list(self._latest_detections)

    # ─────────────────────────────────────────
    # INTERNAL — CAMERA LOOP
    # ─────────────────────────────────────────

    def _start(self, mode):
        if self._running:
            self._mode = mode
            return

        if self._model is None:
            return

        self._mode = mode
        self._running = True
        self._announced.clear()
        self._thread = threading.Thread(target=self._camera_loop, daemon=True)
        self._thread.start()

    def _camera_loop(self):
        """Main loop: captures frames and runs detection at intervals."""
        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            self.speak("I cannot access the camera. Please check the connection.")
            self._running = False
            return

        print(f"📷 Camera started in {self._mode} mode.")
        last_process_time = 0

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            now = time.time()
            if now - last_process_time >= FRAME_INTERVAL:
                last_process_time = now
                detections = self._detect(frame)
                
                # MediaPipe hand detection
                if getattr(self, 'hand_landmarker', None):
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    hand_results = self.hand_landmarker.detect(mp_image)
                else:
                    hand_results = None

                # Store latest detections safely
                with self._det_lock:
                    self._latest_detections = detections
                    self._latest_hand_results = hand_results
                    self._latest_frame_shape = frame.shape

                # Draw annotations on frame
                annotated = self._draw_annotations(frame.copy(), detections, hand_results)
                with self._frame_lock:
                    self._latest_frame = annotated

            else:
                with self._frame_lock:
                    self._latest_frame = frame.copy()

            time.sleep(0.05)

        self._release_camera()

    def _release_camera(self):
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None

    # ─────────────────────────────────────────
    # DETECTION & DESCRIPTION
    # ─────────────────────────────────────────

    def _detect(self, frame):
        """
        Run YOLOv8 on a frame. Returns list of dicts:
        [{"class": str, "confidence": float, "zone": str, "distance": str, "bbox": tuple}]
        """
        results = self._model(frame, verbose=False, conf=CONFIDENCE_THRESHOLD)
        h, w = frame.shape[:2]

        detections = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                cls_name = self._model.names[cls_id]

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                box_area = (x2 - x1) * (y2 - y1)
                frame_area = w * h

                # Position (horizontal)
                if cx < w / 3:
                    zone = "left"
                elif cx < 2 * w / 3:
                    zone = "center"
                else:
                    zone = "right"

                # Distance estimation (based on bounding box area ratio)
                area_ratio = box_area / frame_area
                if area_ratio > 0.15:
                    distance = "very close"
                elif area_ratio > 0.06:
                    distance = "near"
                elif area_ratio > 0.02:
                    distance = "a few meters away"
                else:
                    distance = "far"

                detections.append({
                    "class": cls_name,
                    "confidence": conf,
                    "zone": zone,
                    "distance": distance,
                    "bbox": (int(x1), int(y1), int(x2), int(y2)),
                    "area_ratio": area_ratio,
                })

        return detections

    # (Removed automatic continuous speaking logic to enforce strict command-only mode)

    # ─────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────

    def _add_log_entry(self, obj_class, zone, distance, level="info"):
        """Add a timestamped detection event to the log."""
        entry = {
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "object": obj_class,
            "zone": zone,
            "distance": distance,
            "level": level,
        }
        with self._log_lock:
            self._detection_log.append(entry)

    def _draw_annotations(self, frame, detections, hand_results=None):
        """Draw bounding boxes and labels on the frame."""
        COLORS = {
            "very close": (0, 0, 255),    # Red
            "near":       (0, 165, 255),  # Orange
            "a few meters away": (0, 255, 255),  # Yellow
            "far":        (0, 255, 0),    # Green
        }
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            color = COLORS.get(det["distance"], (255, 255, 255))
            # Draw box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            # Label with background
            label = f"{det['class']} ({det['zone']})"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(frame, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        if getattr(hand_results, 'hand_landmarks', None):
            for hand_landmarks in hand_results.hand_landmarks:
                # Draw just a simple bounding box or dot for the hand based on landmarks
                x_min = int(min([lm.x for lm in hand_landmarks]) * frame.shape[1])
                y_min = int(min([lm.y for lm in hand_landmarks]) * frame.shape[0])
                x_max = int(max([lm.x for lm in hand_landmarks]) * frame.shape[1])
                y_max = int(max([lm.y for lm in hand_landmarks]) * frame.shape[0])
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (255, 0, 255), 2)
                cv2.putText(frame, "HAND", (x_min, y_min - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
                
        return frame

    @staticmethod
    def _direction_text(zone):
        mapping = {
            "left": "on your left",
            "center": "directly ahead",
            "right": "on your right",
        }
        return mapping.get(zone, "ahead")



# ─────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":
    def test_speak(text):
        print(f"🔊 {text}")

    vision = VisionSystem(speak_callback=test_speak)

    print("\n=== One-shot scene description ===")
    desc = vision.describe_scene()
    print(f"📝 {desc}")

    print("\n=== Starting vision mode (press Ctrl+C to stop) ===")
    vision.start_vision_mode()

    try:
        while vision.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        vision.stop()
        print("Done.")
