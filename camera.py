"""
Vision System — Fast Real-Time Object Detection for Blind Users
================================================================
Uses YOLOv8 + MediaPipe for fast object detection and hand tracking.
Gemini Vision API used ONLY as fallback when YOLO can't identify.

Optimized for SPEED — no color processing, fast frame interval.

Author : Arpit
"""

import cv2
import time
import threading
import datetime
import os
from collections import defaultdict, deque
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# ─────────────────────────────────────────────
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️  ultralytics not installed. Run: pip install ultralytics")

try:
    import google.generativeai as genai
    import PIL.Image
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
    GEMINI_VISION = True
except ImportError:
    GEMINI_VISION = False

# ─────────────────────────────────────────────
# CONSTANTS — TUNED FOR SPEED
# ─────────────────────────────────────────────
OBSTACLE_CLASSES = {
    "car", "truck", "bus", "motorcycle", "bicycle",
    "dog", "cat", "horse", "fire hydrant", "stop sign",
    "traffic light", "bench", "chair", "couch", "dining table",
    "suitcase", "backpack", "bed", "toilet", "skateboard",
    "potted plant", "parking meter",
}

HOLDABLE_OBJECTS = {
    "bottle", "cup", "cell phone", "remote", "scissors",
    "toothbrush", "knife", "fork", "spoon", "book",
    "apple", "banana", "orange", "sandwich", "donut",
    "mouse", "keyboard", "umbrella", "handbag",
    "wine glass", "vase", "teddy bear",
}

CONFIDENCE_THRESHOLD = 0.30  # Lower = more detections
FRAME_INTERVAL = 0.8         # Faster processing

# Known widths (cm) for distance estimation
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
FOCAL_LENGTH_PX = 600


def estimate_distance_meters(cls_name, bbox_width_px):
    known_w = KNOWN_WIDTHS.get(cls_name, 30)
    if bbox_width_px < 5:
        return 10.0
    return round((known_w * FOCAL_LENGTH_PX) / bbox_width_px / 100.0, 1)


class VisionSystem:
    def __init__(self, speak_callback=None):
        self.speak = speak_callback or (lambda t: print(f"[VISION] {t}"))
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
                base_options=base_options, num_hands=2,
                min_hand_detection_confidence=0.5, min_tracking_confidence=0.5
            )
            self.hand_landmarker = mp_vision.HandLandmarker.create_from_options(options)
            print("✅ MediaPipe Hand Landmarker loaded successfully.")
        except Exception as e:
            self.hand_landmarker = None
            print(f"❌ Failed to load Hand Landmarker: {e}")

        # Gemini for fallback identification
        self._gemini_model = None
        if GEMINI_VISION:
            try:
                self._gemini_model = genai.GenerativeModel('models/gemini-flash-latest')
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
    # FAST QUERY METHODS (no color, no Gemini unless needed)
    # ─────────────────────────────────────────

    def query_hand(self):
        """Identify what user is holding — YOLO first, Gemini fallback."""
        with self._det_lock:
            hand_results = getattr(self, '_latest_hand_results', None)
            objects = list(self._latest_detections)
            frame_shape = getattr(self, '_latest_frame_shape', None)

        # Strategy 1: MediaPipe hand + YOLO overlap (instant)
        if frame_shape and hand_results and hand_results.hand_landmarks:
            h, w = frame_shape[:2]
            for hand_landmarks, handedness in zip(hand_results.hand_landmarks, hand_results.handedness):
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

        # Strategy 2: Very close holdable object (instant)
        for obj in objects:
            if obj['distance'] == 'very close' and obj['class'] in HOLDABLE_OBJECTS:
                return f"You are holding a {obj['class']}"

        # Strategy 3: Gemini fallback (only if YOLO found nothing)
        raw = self._get_raw_frame()
        if raw is not None and self._gemini_model:
            return self._gemini_quick("What is the person holding? Reply in one sentence like: 'You are holding a pen'. If nothing: 'I cannot detect anything'", raw)

        return "I cannot detect anything in your hand"

    def query_front(self):
        """What's in front — YOLO instant, Gemini fallback."""
        with self._det_lock:
            objects = list(self._latest_detections)

        # YOLO results (instant)
        center = [o for o in objects if o['zone'] == 'center' and o['class'] != 'person']
        center.sort(key=lambda o: o.get('area_ratio', 0), reverse=True)
        if center:
            obj = center[0]
            d = obj.get('distance_m', '')
            return f"{obj['class']} in front of you, about {d} meters away"

        non_person = [o for o in objects if o['class'] != 'person']
        non_person.sort(key=lambda o: o.get('area_ratio', 0), reverse=True)
        if non_person:
            obj = non_person[0]
            return f"{obj['class']} on your {obj['zone']}, about {obj.get('distance_m', '')} meters away"

        # Gemini fallback
        raw = self._get_raw_frame()
        if raw is not None and self._gemini_model:
            return self._gemini_quick("What objects are in front? Name ALL items including small things like pens, glasses, airpods, keys. One sentence.", raw)

        return "Nothing detected in front"

    def query_path(self):
        """Is path clear — YOLO only (fast)."""
        with self._det_lock:
            objects = list(self._latest_detections)
        for obj in objects:
            if obj['zone'] == 'center' and obj['distance'] in ('very close', 'near') and obj['class'] != 'person':
                return f"No, {obj['class']} ahead about {obj.get('distance_m', '')} meters away"
        return "Yes, path is clear"

    def query_person_holding(self):
        """What is the person in front holding."""
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
                return f"The person is holding a {obj['class']}"

        return "I cannot tell what the person is holding"

    def query_distance(self, target=None):
        """Distance of object — YOLO only (fast)."""
        with self._det_lock:
            objects = list(self._latest_detections)
        if target:
            t = target.lower()
            for obj in objects:
                if t in obj['class'].lower():
                    return f"The {obj['class']} is about {obj.get('distance_m', 'unknown')} meters away, {obj['zone']}"
        if objects:
            nearest = min(objects, key=lambda o: o.get('distance_m', 999))
            return f"Nearest: {nearest['class']}, about {nearest.get('distance_m', '')} meters away, {nearest['zone']}"
        return "No objects detected"

    def query_scene_detailed(self):
        """Detailed scene — Gemini (used only on explicit request)."""
        raw = self._get_raw_frame()
        if raw is None:
            return "Camera not ready"

        # Try YOLO first for quick answer
        with self._det_lock:
            objects = list(self._latest_detections)
        if objects and not self._gemini_model:
            items = [f"{o['class']} ({o['zone']}, {o.get('distance_m','')}m)" for o in objects[:5]]
            return "I can see: " + ", ".join(items)

        if self._gemini_model:
            return self._gemini_quick(
                "Describe what you see in 2 short sentences. Name ALL objects including small items. Be specific.", raw)

        return "Nothing detected"

    def describe_scene(self):
        return self.query_scene_detailed()

    # ─────────────────────────────────────────
    # GEMINI HELPER (single method, fast)
    # ─────────────────────────────────────────
    def _gemini_quick(self, prompt, frame):
        """Single Gemini call with timeout-like behavior."""
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = PIL.Image.fromarray(rgb)
            full_prompt = f"You are an assistant for blind users. {prompt}"
            resp = self._gemini_model.generate_content([full_prompt, img])
            return resp.text.strip().split('\n')[0][:150]
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err:
                return "I cannot detect anything else. API quota exceeded."
            return "I cannot detect anything clearly right now."

    def _get_raw_frame(self):
        with self._frame_lock:
            if self._latest_raw_frame is not None:
                return self._latest_raw_frame.copy()
        return None

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
    # CAMERA LOOP
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
            self.speak("I cannot access the camera.")
            self._running = False
            return

        print(f"📷 Camera started in {self._mode} mode.")
        last_process_time = 0

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            with self._frame_lock:
                self._latest_raw_frame = frame.copy()

            now = time.time()
            if now - last_process_time >= FRAME_INTERVAL:
                last_process_time = now
                detections = self._detect(frame)

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

            time.sleep(0.03)

        self._release_camera()

    def _release_camera(self):
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None

    # ─────────────────────────────────────────
    # DETECTION (fast — no color processing)
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

                zone = "left" if cx < w / 3 else ("center" if cx < 2 * w / 3 else "right")

                area_ratio = box_area / frame_area
                if area_ratio > 0.15:
                    distance = "very close"
                elif area_ratio > 0.06:
                    distance = "near"
                elif area_ratio > 0.02:
                    distance = "a few meters away"
                else:
                    distance = "far"

                dist_m = estimate_distance_meters(cls_name, box_w)

                detections.append({
                    "class": cls_name,
                    "confidence": conf,
                    "zone": zone,
                    "distance": distance,
                    "distance_m": dist_m,
                    "bbox": (int(x1), int(y1), int(x2), int(y2)),
                    "area_ratio": area_ratio,
                })

        return detections

    # ─────────────────────────────────────────
    # DRAW ANNOTATIONS (clean labels)
    # ─────────────────────────────────────────
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
            label = f"{det['class']} {det.get('distance_m','')}m"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(frame, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        if getattr(hand_results, 'hand_landmarks', None):
            for hand_landmarks in hand_results.hand_landmarks:
                x_min = int(min(lm.x for lm in hand_landmarks) * frame.shape[1])
                y_min = int(min(lm.y for lm in hand_landmarks) * frame.shape[0])
                x_max = int(max(lm.x for lm in hand_landmarks) * frame.shape[1])
                y_max = int(max(lm.y for lm in hand_landmarks) * frame.shape[0])
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (255, 0, 255), 2)
                cv2.putText(frame, "HAND", (x_min, y_min - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)

        return frame


if __name__ == "__main__":
    def test_speak(text):
        print(f"🔊 {text}")

    vision = VisionSystem(speak_callback=test_speak)
    print("\n=== Starting vision mode (Ctrl+C to stop) ===")
    try:
        while vision.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        vision.stop()
        print("Done.")
