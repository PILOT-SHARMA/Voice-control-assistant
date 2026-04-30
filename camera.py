"""
Vision System — Real-Time Object Detection for Blind Users
===========================================================
Uses YOLOv8 + MediaPipe + Color Analysis + Gemini AI for comprehensive
object detection, hand tracking, color identification, and distance estimation.

Features:
  • YOLOv8n for fast real-time object detection (80 COCO classes)
  • Gemini Vision API for detailed recognition (airpods, pens, glasses, etc.)
  • HSV-based color identification
  • Approximate distance estimation in meters
  • MediaPipe hand landmark tracking
  • Thread-safe callback system for TTS

Author : Arpit
"""

import cv2
import time
import threading
import datetime
import numpy as np
import os
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
# TRY TO IMPORT GEMINI FOR DETAILED RECOGNITION
# ─────────────────────────────────────────────
try:
    import google.generativeai as genai
    import PIL.Image
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
    GEMINI_VISION = True
except ImportError:
    GEMINI_VISION = False

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
OBSTACLE_CLASSES = {
    "car", "truck", "bus", "motorcycle", "bicycle",
    "dog", "cat", "horse",
    "fire hydrant", "stop sign", "traffic light",
    "bench", "chair", "couch", "dining table",
    "suitcase", "backpack", "bed", "toilet",
    "skateboard", "snowboard", "surfboard",
    "potted plant", "parking meter",
}

HOLDABLE_OBJECTS = {
    "bottle", "cup", "cell phone", "remote", "scissors",
    "toothbrush", "knife", "fork", "spoon", "book",
    "apple", "banana", "orange", "sandwich", "donut",
    "mouse", "keyboard", "umbrella", "handbag",
    "wine glass", "vase", "teddy bear",
}

CONFIDENCE_THRESHOLD = 0.35
ANNOUNCE_COOLDOWN = 8.0
FRAME_INTERVAL = 1.2

# Known average widths (cm) for distance estimation
KNOWN_WIDTHS = {
    "person": 45, "car": 180, "truck": 250, "bus": 280,
    "motorcycle": 80, "bicycle": 60, "chair": 50, "couch": 180,
    "bottle": 8, "cup": 8, "cell phone": 7, "laptop": 35,
    "keyboard": 45, "mouse": 6, "remote": 5, "book": 15,
    "tv": 100, "refrigerator": 70, "bed": 150, "dining table": 120,
    "dog": 40, "cat": 25, "backpack": 35, "umbrella": 25,
    "handbag": 30, "suitcase": 50, "apple": 8, "banana": 15,
    "orange": 8, "scissors": 10, "toothbrush": 3, "clock": 25,
}
FOCAL_LENGTH_PX = 600  # approximate for standard webcam

# ─────────────────────────────────────────────
# COLOR DETECTION
# ─────────────────────────────────────────────
COLOR_RANGES = [
    ("red",      [(0, 70, 50), (10, 255, 255)]),
    ("red",      [(170, 70, 50), (180, 255, 255)]),
    ("orange",   [(11, 70, 50), (25, 255, 255)]),
    ("yellow",   [(26, 70, 50), (34, 255, 255)]),
    ("green",    [(35, 70, 50), (85, 255, 255)]),
    ("blue",     [(86, 70, 50), (130, 255, 255)]),
    ("purple",   [(131, 70, 50), (160, 255, 255)]),
    ("pink",     [(161, 70, 50), (169, 255, 255)]),
]

def detect_color(frame, bbox):
    """Extract dominant color from bounding box region using HSV analysis."""
    x1, y1, x2, y2 = bbox
    h, w = frame.shape[:2]
    # Clamp to frame
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 - x1 < 5 or y2 - y1 < 5:
        return "unknown"

    # Take center 60% of the ROI to avoid edges
    cx, cy = (x2 - x1) // 5, (y2 - y1) // 5
    roi = frame[y1 + cy:y2 - cy, x1 + cx:x2 - cx]
    if roi.size == 0:
        roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return "unknown"

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Check for achromatic colors first (black, white, gray)
    avg_s = np.mean(hsv[:, :, 1])
    avg_v = np.mean(hsv[:, :, 2])

    if avg_v < 40:
        return "black"
    if avg_s < 30 and avg_v > 200:
        return "white"
    if avg_s < 40:
        return "gray"
    if avg_s < 50 and 80 < avg_v < 200:
        return "gray"

    # Check chromatic colors
    best_color = "unknown"
    best_count = 0
    for name, (lower, upper) in COLOR_RANGES:
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        count = cv2.countNonZero(mask)
        if count > best_count:
            best_count = count
            best_color = name

    total_px = hsv.shape[0] * hsv.shape[1]
    if best_count < total_px * 0.1:
        # Less than 10% match — use average hue
        avg_h = np.mean(hsv[:, :, 0])
        if avg_h < 10 or avg_h > 170:
            return "red"
        elif avg_h < 25:
            return "orange"
        elif avg_h < 35:
            return "yellow"
        elif avg_h < 85:
            return "green"
        elif avg_h < 130:
            return "blue"
        elif avg_h < 160:
            return "purple"
        else:
            return "pink"

    return best_color


def estimate_distance_meters(cls_name, bbox_width_px):
    """Estimate distance in meters using known object widths."""
    known_w = KNOWN_WIDTHS.get(cls_name, 30)  # default 30cm
    if bbox_width_px < 5:
        return 10.0
    dist_cm = (known_w * FOCAL_LENGTH_PX) / bbox_width_px
    return round(dist_cm / 100.0, 1)


class VisionSystem:
    """
    Manages webcam, YOLOv8 inference, MediaPipe hands, color detection,
    distance estimation, and Gemini-based detailed recognition.
    """

    def __init__(self, speak_callback=None):
        self.speak = speak_callback or (lambda t: print(f"[VISION] {t}"))

        # State
        self._running = False
        self._thread = None
        self._cap = None
        self._mode = "off"
        self._lock = threading.Lock()
        self._announced = defaultdict(float)

        # Load YOLOv8
        self._model = None
        if YOLO_AVAILABLE:
            try:
                self._model = YOLO("yolov8n.pt")
                print("✅ YOLOv8n model loaded successfully.")
            except Exception as e:
                print(f"❌ Failed to load YOLO model: {e}")

        # Load MediaPipe Hands
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

        # Gemini model for detailed recognition
        self._gemini_model = None
        if GEMINI_VISION:
            try:
                self._gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                print("✅ Gemini Vision model ready.")
            except Exception:
                pass

        # Thread-safe storage
        self._latest_frame = None
        self._latest_raw_frame = None
        self._frame_lock = threading.Lock()
        self._detection_log = deque(maxlen=50)
        self._log_lock = threading.Lock()
        self._latest_detections = []
        self._latest_hand_results = None
        self._latest_frame_shape = None
        self._det_lock = threading.Lock()

        # Gemini cache for detailed queries
        self._gemini_cache = {"text": None, "t": 0}
        self._gemini_lock = threading.Lock()

        # Auto-start
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
        self._start("vision")

    def start_navigation_mode(self):
        self._start("navigation")

    def stop(self):
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

    # ─────────────────────────────────────────
    # QUERY METHODS
    # ─────────────────────────────────────────

    def query_hand(self):
        with self._det_lock:
            hand_results = getattr(self, '_latest_hand_results', None)
            objects = list(self._latest_detections)
            frame_shape = getattr(self, '_latest_frame_shape', None)

        raw_frame = None
        with self._frame_lock:
            if self._latest_raw_frame is not None:
                raw_frame = self._latest_raw_frame.copy()

        # Strategy 1: MediaPipe overlap
        if frame_shape and hand_results and hand_results.hand_landmarks:
            h, w = frame_shape[:2]
            for hand_landmarks, handedness in zip(hand_results.hand_landmarks, hand_results.handedness):
                hand_label = handedness[0].category_name
                x_min = min(lm.x for lm in hand_landmarks) * w
                y_min = min(lm.y for lm in hand_landmarks) * h
                x_max = max(lm.x for lm in hand_landmarks) * w
                y_max = max(lm.y for lm in hand_landmarks) * h
                for obj in objects:
                    if obj['class'] == 'person':
                        continue
                    ox1, oy1, ox2, oy2 = obj['bbox']
                    if x_min < ox2 and x_max > ox1 and y_min < oy2 and y_max > oy1:
                        color = obj.get('color', '')
                        c_str = f"{color} " if color and color != 'unknown' else ""
                        return f"You are holding a {c_str}{obj['class']}"

        # Strategy 2: Fallback holdable
        for obj in objects:
            if obj['distance'] == 'very close' and obj['class'] in HOLDABLE_OBJECTS:
                color = obj.get('color', '')
                c_str = f"{color} " if color and color != 'unknown' else ""
                return f"You are holding a {c_str}{obj['class']}"

        # Strategy 3: Ask Gemini for hand region
        if raw_frame is not None and self._gemini_model:
            return self._gemini_hand_query(raw_frame)

        return "I cannot detect anything in your hand"

    def _gemini_hand_query(self, frame):
        """Use Gemini to identify what's in the hand."""
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = PIL.Image.fromarray(rgb)
            prompt = ("You are an assistant for blind users. Look at this image. "
                      "What is the person holding in their hand? "
                      "Reply in exactly one short sentence like: 'You are holding a pen' "
                      "If nothing, say 'I cannot detect anything in your hand'")
            resp = self._gemini_model.generate_content([prompt, img])
            return resp.text.strip().split('\n')[0][:100]
        except Exception:
            return "I cannot detect anything in your hand"

    def query_front(self):
        with self._det_lock:
            objects = list(self._latest_detections)

        center = [o for o in objects if o['zone'] == 'center' and o['class'] != 'person']
        center.sort(key=lambda o: o.get('area_ratio', 0), reverse=True)

        if center:
            obj = center[0]
            dist = obj.get('distance_m', '')
            d_str = f", about {dist} meters away" if dist else ""
            return f"{obj['class']} in front of you{d_str}"

        non_person = [o for o in objects if o['class'] != 'person']
        non_person.sort(key=lambda o: o.get('area_ratio', 0), reverse=True)
        if non_person:
            obj = non_person[0]
            return f"{obj['class']} {obj['zone']}, {obj.get('distance_m', '')} meters away"

        return "Nothing detected in front"

    def query_path(self):
        with self._det_lock:
            objects = list(self._latest_detections)

        for obj in objects:
            if obj['zone'] == 'center' and obj['distance'] in ('very close', 'near') and obj['class'] != 'person':
                d = obj.get('distance_m', '')
                return f"No, {obj['class']} ahead about {d} meters away"

        return "Yes, path is clear"

    def query_person_holding(self):
        with self._det_lock:
            objects = list(self._latest_detections)

        person_objs = [o for o in objects if o['class'] == 'person' and o['distance'] != 'very close']
        if not person_objs:
            return "I cannot see a person in front"

        person = person_objs[0]
        px1, py1, px2, py2 = person['bbox']
        margin = 40
        epx1, epy1, epx2, epy2 = px1 - margin, py1 - margin, px2 + margin, py2 + margin

        for obj in objects:
            if obj['class'] == 'person':
                continue
            ox1, oy1, ox2, oy2 = obj['bbox']
            if ox1 < epx2 and ox2 > epx1 and oy1 < epy2 and oy2 > epy1:
                return f"The person in front is holding a {obj['class']}"

        return "I cannot tell what the person is holding"

    def query_color(self, target=None):
        """Query the color of an object or clothing."""
        with self._det_lock:
            objects = list(self._latest_detections)

        if target:
            t = target.lower()
            for obj in objects:
                if t in obj['class'].lower():
                    c = obj.get('color', 'unknown')
                    return f"The {obj['class']} is {c}"
            # Check clothing on person
            if any(w in t for w in ['cloth', 'shirt', 'wear', 'kapda', 'dress']):
                persons = [o for o in objects if o['class'] == 'person']
                if persons:
                    c = persons[0].get('color', 'unknown')
                    return f"The clothing color appears to be {c}"

        # Default: describe colors of all visible objects
        if objects:
            descs = []
            for obj in objects[:3]:
                c = obj.get('color', 'unknown')
                if c != 'unknown':
                    descs.append(f"{c} {obj['class']}")
            if descs:
                return "I can see: " + ", ".join(descs)

        return "I cannot determine the color right now"

    def query_distance(self, target=None):
        """Query distance of a specific object or nearest object."""
        with self._det_lock:
            objects = list(self._latest_detections)

        if target:
            t = target.lower()
            for obj in objects:
                if t in obj['class'].lower():
                    d = obj.get('distance_m', 'unknown')
                    return f"The {obj['class']} is about {d} meters away, {obj['zone']}"

        # Default: nearest object
        if objects:
            nearest = min(objects, key=lambda o: o.get('distance_m', 999))
            d = nearest.get('distance_m', 'unknown')
            return f"Nearest object is {nearest['class']}, about {d} meters away, {nearest['zone']}"

        return "No objects detected"

    def query_scene_detailed(self):
        """Use Gemini to give a detailed scene description."""
        raw_frame = None
        with self._frame_lock:
            if self._latest_raw_frame is not None:
                raw_frame = self._latest_raw_frame.copy()

        if raw_frame is None:
            return "Camera not ready"

        # Cache for 5 seconds
        with self._gemini_lock:
            if time.time() - self._gemini_cache["t"] < 5 and self._gemini_cache["text"]:
                return self._gemini_cache["text"]

        if not self._gemini_model:
            # Fallback to YOLO detections
            with self._det_lock:
                objects = list(self._latest_detections)
            if objects:
                items = [f"{o['class']} ({o['zone']}, {o.get('distance_m','')}m)" for o in objects[:5]]
                return "I can see: " + ", ".join(items)
            return "Nothing detected"

        try:
            rgb = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2RGB)
            img = PIL.Image.fromarray(rgb)
            prompt = ("You are an assistant for blind users. Describe what you see in 2-3 short sentences. "
                      "Mention ALL objects including small items like pens, glasses, airpods, keys, etc. "
                      "Include colors and approximate distances. Be specific and helpful.")
            resp = self._gemini_model.generate_content([prompt, img])
            result = resp.text.strip()[:200]
            with self._gemini_lock:
                self._gemini_cache = {"text": result, "t": time.time()}
            return result
        except Exception as e:
            return f"Scene analysis unavailable: {str(e)[:50]}"

    def describe_scene(self):
        """Backward compatibility wrapper."""
        return self.query_scene_detailed()

    # ─────────────────────────────────────────
    # DATA ACCESS
    # ─────────────────────────────────────────

    def get_latest_frame(self):
        with self._frame_lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def get_detection_log(self, count=20):
        with self._log_lock:
            return list(self._detection_log)[-count:]

    def get_latest_detections(self):
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

            # Store raw frame for Gemini queries
            with self._frame_lock:
                self._latest_raw_frame = frame.copy()

            now = time.time()
            if now - last_process_time >= FRAME_INTERVAL:
                last_process_time = now
                detections = self._detect(frame)

                # MediaPipe hand detection
                if getattr(self, 'hand_landmarker', None):
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,
                                        data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    hand_results = self.hand_landmarker.detect(mp_image)
                else:
                    hand_results = None

                with self._det_lock:
                    self._latest_detections = detections
                    self._latest_hand_results = hand_results
                    self._latest_frame_shape = frame.shape

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
    # DETECTION
    # ─────────────────────────────────────────

    def _detect(self, frame):
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
                box_w = x2 - x1
                box_area = box_w * (y2 - y1)
                frame_area = w * h

                # Zone
                if cx < w / 3:
                    zone = "left"
                elif cx < 2 * w / 3:
                    zone = "center"
                else:
                    zone = "right"

                # Distance (qualitative)
                area_ratio = box_area / frame_area
                if area_ratio > 0.15:
                    distance = "very close"
                elif area_ratio > 0.06:
                    distance = "near"
                elif area_ratio > 0.02:
                    distance = "a few meters away"
                else:
                    distance = "far"

                # Distance in meters
                dist_m = estimate_distance_meters(cls_name, box_w)

                # Color
                color = detect_color(frame, (int(x1), int(y1), int(x2), int(y2)))

                detections.append({
                    "class": cls_name,
                    "confidence": conf,
                    "zone": zone,
                    "distance": distance,
                    "distance_m": dist_m,
                    "color": color,
                    "bbox": (int(x1), int(y1), int(x2), int(y2)),
                    "area_ratio": area_ratio,
                })

        return detections

    # ─────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────

    def _add_log_entry(self, obj_class, zone, distance, level="info"):
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
        COLORS = {
            "very close": (0, 0, 255),
            "near":       (0, 165, 255),
            "a few meters away": (0, 255, 255),
            "far":        (0, 255, 0),
        }
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            color = COLORS.get(det["distance"], (255, 255, 255))
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            # Label with distance + color
            d_m = det.get('distance_m', '')
            c_name = det.get('color', '')
            label = f"{det['class']} {d_m}m"
            if c_name and c_name != 'unknown':
                label = f"{c_name} {det['class']} {d_m}m"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(frame, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        if getattr(hand_results, 'hand_landmarks', None):
            for hand_landmarks in hand_results.hand_landmarks:
                x_min = int(min([lm.x for lm in hand_landmarks]) * frame.shape[1])
                y_min = int(min([lm.y for lm in hand_landmarks]) * frame.shape[0])
                x_max = int(max([lm.x for lm in hand_landmarks]) * frame.shape[1])
                y_max = int(max([lm.y for lm in hand_landmarks]) * frame.shape[0])
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (255, 0, 255), 2)
                cv2.putText(frame, "HAND", (x_min, y_min - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)

        return frame

    @staticmethod
    def _direction_text(zone):
        return {"left": "on your left", "center": "directly ahead", "right": "on your right"}.get(zone, "ahead")


# ─────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":
    def test_speak(text):
        print(f"🔊 {text}")

    vision = VisionSystem(speak_callback=test_speak)
    print("\n=== Starting vision mode (press Ctrl+C to stop) ===")
    try:
        while vision.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        vision.stop()
        print("Done.")
